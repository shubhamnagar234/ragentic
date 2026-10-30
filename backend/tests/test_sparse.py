"""
Unit tests for BM25 multi-source indexing, persistence, and source-filtered retrieval.
"""

import unittest
import asyncio
import json
from unittest.mock import patch
import redis

from app.services.retrieval.sparse import (
    save_index_to_redis,
    load_index_from_redis,
    sparse_search,
    delete_source_from_redis,
    _merge_chunks,
    _normalize_chunk,
)


class FakeRedisPipeline:
    def __init__(self, store):
        self.store = store
        self.watches = set()
        self.watched_versions = {}
        self.commands = []
        self.in_multi = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.reset()

    def reset(self):
        self.watches.clear()
        self.watched_versions.clear()
        self.commands.clear()
        self.in_multi = False

    def close(self):
        self.reset()

    def watch(self, *keys):
        for k in keys:
            self.watches.add(k)
            self.watched_versions[k] = self.store.get_version(k)

    def get(self, key):
        return self.store.get(key)

    def multi(self):
        self.in_multi = True

    def set(self, key, value, ex=None):
        if self.in_multi:
            self.commands.append(("set", key, value, ex))
        else:
            self.store.set(key, value, ex)

    def delete(self, key):
        if self.in_multi:
            self.commands.append(("delete", key))
        else:
            self.store.delete(key)

    def execute(self):
        # Optimistic locking check: did any watched key change?
        for k in self.watches:
            if self.store.get_version(k) != self.watched_versions.get(k):
                raise redis.WatchError("Watched key was modified by another transaction")

        results = []
        for cmd in self.commands:
            if cmd[0] == "set":
                results.append(self.store.set(cmd[1], cmd[2], cmd[3]))
            elif cmd[0] == "delete":
                results.append(self.store.delete(cmd[1]))
        self.commands.clear()
        self.in_multi = False
        return results


class FakeRedisStore:
    def __init__(self):
        self._data = {}
        self._versions = {}
        self.closed = False

    def get(self, key):
        return self._data.get(key)

    def get_version(self, key):
        return self._versions.get(key, 0)

    def set(self, key, value, ex=None):
        self._data[key] = value
        self._versions[key] = self._versions.get(key, 0) + 1
        return True

    def delete(self, key):
        self._data.pop(key, None)
        self._versions[key] = self._versions.get(key, 0) + 1
        return True

    def pipeline(self):
        return FakeRedisPipeline(self)

    def close(self):
        self.closed = True


class TestBM25MultiSourceIndexing(unittest.TestCase):
    def setUp(self):
        self.fake_redis = FakeRedisStore()
        self.patcher = patch(
            "app.services.retrieval.sparse.get_redis_client",
            return_value=self.fake_redis,
        )
        self.mock_client = self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_saving_chunks_persists_source_id(self):
        """source_id must be stored in Redis alongside chunk_id and text."""
        chunks = [
            {"chunk_id": "c1", "text": "Python asynchronous programming", "source_id": "src-101"},
            {"chunk_id": "c2", "text": "FastAPI dependency injection", "source_id": "src-101"},
        ]
        save_index_to_redis("ws-1", chunks)

        loaded = load_index_from_redis("ws-1")
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0]["chunk_id"], "c1")
        self.assertEqual(loaded[0]["source_id"], "src-101")
        self.assertEqual(loaded[1]["chunk_id"], "c2")
        self.assertEqual(loaded[1]["source_id"], "src-101")

    def test_ingesting_source_a_then_source_b_preserves_both(self):
        """Ingesting a second source into a workspace must preserve the first source's chunks."""
        chunks_a = [
            {"chunk_id": "c1", "text": "PostgreSQL database indices", "source_id": "src-A"},
            {"chunk_id": "c2", "text": "Write-ahead logging and MVCC", "source_id": "src-A"},
        ]
        chunks_b = [
            {"chunk_id": "c3", "text": "Redis caching and TTL policies", "source_id": "src-B"},
        ]

        save_index_to_redis("ws-1", chunks_a)
        save_index_to_redis("ws-1", chunks_b)

        loaded = load_index_from_redis("ws-1")
        self.assertEqual(len(loaded), 3)

        source_a_chunks = [c for c in loaded if c.get("source_id") == "src-A"]
        source_b_chunks = [c for c in loaded if c.get("source_id") == "src-B"]
        self.assertEqual(len(source_a_chunks), 2)
        self.assertEqual(len(source_b_chunks), 1)

    def test_reingesting_source_a_replaces_old_chunks_without_duplicates(self):
        """Re-ingesting source A must replace its old chunks without touching source B or duplicating."""
        chunks_a1 = [
            {"chunk_id": "c1", "text": "Initial text of chunk 1", "source_id": "src-A"},
            {"chunk_id": "c2", "text": "Initial text of chunk 2", "source_id": "src-A"},
        ]
        chunks_b = [
            {"chunk_id": "c3", "text": "Redis caching mechanism", "source_id": "src-B"},
        ]
        save_index_to_redis("ws-1", chunks_a1)
        save_index_to_redis("ws-1", chunks_b)

        # Re-ingest source A with updated text and one new chunk, removing c2
        chunks_a2 = [
            {"chunk_id": "c1", "text": "Updated text of chunk 1", "source_id": "src-A"},
            {"chunk_id": "c4", "text": "Brand new chunk 4", "source_id": "src-A"},
        ]
        save_index_to_redis("ws-1", chunks_a2)

        loaded = load_index_from_redis("ws-1")
        self.assertEqual(len(loaded), 3)  # c3 (src-B), c1 (src-A updated), c4 (src-A new)

        chunk_map = {c["chunk_id"]: c for c in loaded}
        self.assertIn("c1", chunk_map)
        self.assertEqual(chunk_map["c1"]["text"], "Updated text of chunk 1")
        self.assertNotIn("c2", chunk_map)  # pruned from old source-A
        self.assertIn("c3", chunk_map)      # src-B preserved untouched
        self.assertIn("c4", chunk_map)

    def test_searching_without_source_filters_searches_all_sources(self):
        """Searching without source_ids must search across all chunks in the workspace."""
        chunks = [
            {"chunk_id": "c1", "text": "neural network embeddings and vector math", "source_id": "src-A"},
            {"chunk_id": "c2", "text": "relational database normalization and tables", "source_id": "src-B"},
            {"chunk_id": "c3", "text": "unrelated audio transcript recording", "source_id": "src-C"},
        ]
        save_index_to_redis("ws-1", chunks)

        results = asyncio.run(sparse_search(query="neural", workspace_id="ws-1", top_k=10, source_ids=None))
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0]["chunk_id"], "c1")

        results_db = asyncio.run(sparse_search(query="relational", workspace_id="ws-1", top_k=10, source_ids=None))
        self.assertGreater(len(results_db), 0)
        self.assertEqual(results_db[0]["chunk_id"], "c2")

    def test_searching_with_source_a_returns_only_source_a(self):
        """Source filtering must return only matching source chunks even if query matches other sources."""
        chunks = [
            {"chunk_id": "c1", "text": "common keyword in source A", "source_id": "src-A"},
            {"chunk_id": "c2", "text": "common keyword in source B", "source_id": "src-B"},
        ]
        save_index_to_redis("ws-1", chunks)

        results_a = asyncio.run(sparse_search(
            query="keyword", workspace_id="ws-1", top_k=10, source_ids=["src-A"]
        ))
        self.assertEqual(len(results_a), 1)
        self.assertEqual(results_a[0]["chunk_id"], "c1")
        self.assertEqual(results_a[0]["source_id"], "src-A")

        results_b = asyncio.run(sparse_search(
            query="keyword", workspace_id="ws-1", top_k=10, source_ids=["src-B"]
        ))
        self.assertEqual(len(results_b), 1)
        self.assertEqual(results_b[0]["chunk_id"], "c2")
        self.assertEqual(results_b[0]["source_id"], "src-B")

    def test_workspace_isolation(self):
        """A search in workspace-1 must never return chunks stored in workspace-2."""
        save_index_to_redis("ws-1", [{"chunk_id": "c1", "text": "machine learning in ws1", "source_id": "s1"}])
        save_index_to_redis("ws-2", [{"chunk_id": "c2", "text": "machine learning in ws2", "source_id": "s2"}])

        results_ws1 = asyncio.run(sparse_search(query="machine", workspace_id="ws-1"))
        self.assertEqual(len(results_ws1), 1)
        self.assertEqual(results_ws1[0]["chunk_id"], "c1")

        results_ws2 = asyncio.run(sparse_search(query="machine", workspace_id="ws-2"))
        self.assertEqual(len(results_ws2), 1)
        self.assertEqual(results_ws2[0]["chunk_id"], "c2")

    def test_empty_index_returns_empty_list(self):
        """Querying a non-existent or empty workspace index returns an empty list."""
        results = asyncio.run(sparse_search(query="anything", workspace_id="non-existent-ws"))
        self.assertEqual(results, [])

    def test_legacy_redis_records_handled_safely(self):
        """Legacy chunks stored without source_id must be preserved and not given fake source IDs."""
        legacy_data = [
            {"chunk_id": "leg-1", "text": "legacy document text without source id"}
        ]
        self.fake_redis.set("bm25:ws-legacy", json.dumps(legacy_data))

        # Search without source filter -> legacy chunk is found
        results = asyncio.run(sparse_search(query="legacy", workspace_id="ws-legacy", source_ids=None))
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["chunk_id"], "leg-1")
        self.assertIsNone(results[0]["source_id"])

        # Search with source_ids filter -> legacy chunk does NOT falsely match
        filtered = asyncio.run(sparse_search(query="legacy", workspace_id="ws-legacy", source_ids=["src-X"]))
        self.assertEqual(len(filtered), 0)

        # Ingesting new source into ws-legacy keeps legacy chunk intact
        new_chunks = [{"chunk_id": "new-1", "text": "new source content", "source_id": "src-new"}]
        save_index_to_redis("ws-legacy", new_chunks)
        loaded = load_index_from_redis("ws-legacy")
        self.assertEqual(len(loaded), 2)
        chunk_map = {c["chunk_id"]: c for c in loaded}
        self.assertIn("leg-1", chunk_map)
        self.assertIsNone(chunk_map["leg-1"].get("source_id"))
        self.assertIn("new-1", chunk_map)
        self.assertEqual(chunk_map["new-1"].get("source_id"), "src-new")

    def test_delete_source_from_redis(self):
        """delete_source_from_redis must remove only the target source's chunks."""
        chunks = [
            {"chunk_id": "c1", "text": "text of source 1", "source_id": "src-1"},
            {"chunk_id": "c2", "text": "text of source 2", "source_id": "src-2"},
        ]
        save_index_to_redis("ws-del", chunks)

        delete_source_from_redis("ws-del", "src-1")
        remaining = load_index_from_redis("ws-del")
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["source_id"], "src-2")

    def test_concurrent_updates_optimistic_retry(self):
        """Simulates concurrent modification triggering WatchError on first attempt, then succeeding on retry."""
        save_index_to_redis("ws-concur", [{"chunk_id": "c1", "text": "base chunk", "source_id": "s1"}])

        attempt_counter = [0]
        original_watch = FakeRedisPipeline.watch

        def race_condition_watch(pipe_self, *keys):
            original_watch(pipe_self, *keys)
            attempt_counter[0] += 1
            if attempt_counter[0] == 1:
                # Simulate another worker updating the key between WATCH and EXEC
                pipe_self.store.set("bm25:ws-concur", json.dumps([
                    {"chunk_id": "c1", "text": "base chunk", "source_id": "s1"},
                    {"chunk_id": "c2", "text": "concurrently inserted chunk", "source_id": "s2"},
                ]))

        with patch.object(FakeRedisPipeline, "watch", side_effect=race_condition_watch, autospec=True):
            # This save should hit WatchError on attempt 1, re-read on attempt 2, and succeed
            save_index_to_redis("ws-concur", [{"chunk_id": "c3", "text": "my new chunk", "source_id": "s3"}])

        loaded = load_index_from_redis("ws-concur")
        chunk_ids = {c["chunk_id"] for c in loaded}
        self.assertIn("c1", chunk_ids)
        self.assertIn("c2", chunk_ids)  # concurrent chunk preserved!
        self.assertIn("c3", chunk_ids)  # my new chunk saved!
        self.assertEqual(attempt_counter[0], 2)  # verified retry happened

    def test_merge_chunks_rejects_conflicting_source_ids_within_incoming(self):
        """Incoming chunks containing the same chunk_id with different source_ids must raise ValueError."""
        incoming = [
            {"chunk_id": "c_dup", "text": "Text version A", "source_id": "source-alpha"},
            {"chunk_id": "c_dup", "text": "Text version B", "source_id": "source-beta"},
        ]
        with self.assertRaises(ValueError) as ctx:
            _merge_chunks([], incoming)
        self.assertIn("Conflicting source_id detected for incoming chunk_id 'c_dup'", str(ctx.exception))

    def test_merge_chunks_rejects_conflicting_source_ownership_against_existing(self):
        """Incoming chunk with chunk_id already owned by a different existing source must raise ValueError."""
        existing = [
            {"chunk_id": "shared_c1", "text": "Existing owned by src-1", "source_id": "src-1"},
            {"chunk_id": "other_c2", "text": "Existing owned by src-1", "source_id": "src-1"},
        ]
        incoming = [
            {"chunk_id": "shared_c1", "text": "Conflicting claim by src-2", "source_id": "src-2"},
        ]
        with self.assertRaises(ValueError) as ctx:
            _merge_chunks(existing, incoming)
        self.assertIn("Conflicting source ownership for chunk_id 'shared_c1'", str(ctx.exception))
        self.assertIn("src-1", str(ctx.exception))
        self.assertIn("src-2", str(ctx.exception))

    def test_merge_chunks_resolves_duplicate_incoming_ids_same_source(self):
        """Incoming chunks with same chunk_id and same source_id should be deduped without error."""
        incoming = [
            {"chunk_id": "c1", "text": "Initial version", "source_id": "src-1"},
            {"chunk_id": "c1", "text": "Revised version", "source_id": "src-1"},
        ]
        merged = _merge_chunks([], incoming)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["chunk_id"], "c1")
        self.assertEqual(merged[0]["text"], "Revised version")
        self.assertEqual(merged[0]["source_id"], "src-1")

    def test_sparse_search_zero_lexical_matches_returns_empty(self):
        """Query with zero token overlap across all chunks must return an empty list."""
        chunks = [
            {"chunk_id": "c1", "text": "linear regression gradient descent machine learning", "source_id": "s1"},
            {"chunk_id": "c2", "text": "neural network backpropagation deep learning", "source_id": "s1"},
        ]
        save_index_to_redis("ws-zero", chunks)

        # Completely disjoint query tokens
        results = asyncio.run(sparse_search(query="xylophone zebra pineapple", workspace_id="ws-zero"))
        self.assertEqual(results, [])

    def test_sparse_search_small_corpus_idf_edge_cases(self):
        """Small corpus (N=1 and N=2) where RSJ IDF is <= 0 must still return matching chunks with positive adjusted scores."""
        # Case 1: Single chunk in index (N=1, n=1 -> standard RSJ IDF <= 0)
        single_chunk = [
            {"chunk_id": "single_c1", "text": "quantum computing qubits entanglement", "source_id": "src-qc"}
        ]
        save_index_to_redis("ws-small-1", single_chunk)

        res_1 = asyncio.run(sparse_search(query="qubits quantum", workspace_id="ws-small-1"))
        self.assertEqual(len(res_1), 1)
        self.assertEqual(res_1[0]["chunk_id"], "single_c1")
        self.assertGreater(res_1[0]["score"], 0.0)

        # Case 2: Two chunks in index (N=2, n=1 -> IDF is 0 in standard Robertson-Spärck Jones)
        two_chunks = [
            {"chunk_id": "tc1", "text": "photosynthesis chloroplasts chlorophyll plant biology", "source_id": "src-bio"},
            {"chunk_id": "tc2", "text": "cellular respiration mitochondria energy metabolism", "source_id": "src-bio"},
        ]
        save_index_to_redis("ws-small-2", two_chunks)

        res_2 = asyncio.run(sparse_search(query="chlorophyll", workspace_id="ws-small-2"))
        self.assertEqual(len(res_2), 1)
        self.assertEqual(res_2[0]["chunk_id"], "tc1")
        self.assertGreater(res_2[0]["score"], 0.0)

    def test_shared_client_dependency_injection_not_closed(self):
        """When client is provided via dependency injection, the functions must NOT close it."""
        di_client = FakeRedisStore()
        save_index_to_redis("ws-di", [{"chunk_id": "c1", "text": "DI chunk", "source_id": "s1"}], client=di_client)
        self.assertFalse(di_client.closed, "save_index_to_redis must not close injected shared client")

        loaded = load_index_from_redis("ws-di", client=di_client)
        self.assertEqual(len(loaded), 1)
        self.assertFalse(di_client.closed, "load_index_from_redis must not close injected shared client")

        delete_source_from_redis("ws-di", "s1", client=di_client)
        self.assertFalse(di_client.closed, "delete_source_from_redis must not close injected shared client")


if __name__ == "__main__":
    unittest.main()
