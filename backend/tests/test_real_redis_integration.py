import unittest
import uuid
import json
import asyncio
import threading
import concurrent.futures
from typing import List, Dict, Any
import redis

from app.config import settings
from app.services.retrieval.sparse import (
    save_index_to_redis,
    load_index_from_redis,
    delete_source_from_redis,
    sparse_search,
)

TEST_REDIS_URL = "redis://localhost:6380/0"


def check_port_6380() -> bool:
    try:
        r = redis.from_url(TEST_REDIS_URL, socket_timeout=1)
        return bool(r.ping())
    except Exception:
        return False


REDIS_6380_AVAILABLE = check_port_6380()


@unittest.skipUnless(REDIS_6380_AVAILABLE, "Isolated Redis 7 test container at redis://localhost:6380/0 is unreachable")
class TestRealRedisIntegration(unittest.TestCase):
    """
    Integration tests against a REAL Redis 7 instance on redis://localhost:6380/0.
    Verifies:
    1. Saving chunks with source_id metadata
    2. Searching across multiple sources in one workspace
    3. Filtering search results by source_id
    4. Re-ingesting a source without duplicating chunks
    5. Preserving other sources when one source is re-ingested
    6. Deleting one source without affecting other sources
    7. Isolating indexes between workspaces
    8. Handling concurrent updates using separate real Redis connections

    Safety Guarantees:
    - Never connects to or modifies Redis on port 6379.
    - Flushes only database 0 on port 6380 before and after each test.
    - Uses unique workspace UUIDs for each test.
    """

    def setUp(self):
        # Save original settings
        self.orig_redis_url = settings.REDIS_URL
        self.created_workspaces: List[str] = []

        try:
            # Point app settings to the isolated test container on port 6380
            settings.REDIS_URL = TEST_REDIS_URL

            # Create direct client for assertions and key-level cleanup
            self.client = redis.from_url(TEST_REDIS_URL)

            # Strict safety verification: MUST be port 6380
            conn_port = self.client.connection_pool.connection_kwargs.get("port")
            assert conn_port == 6380, f"SAFETY ABORT: Expected port 6380, got {conn_port}"

            # Unique workspace ID per test
            self.workspace_id = f"test-ws-{uuid.uuid4().hex[:8]}"
            self.created_workspaces.append(self.workspace_id)
        except Exception:
            settings.REDIS_URL = self.orig_redis_url
            raise

    def tearDown(self):
        try:
            # Safely delete ONLY test-owned keys; never call flushdb()
            for ws in self.created_workspaces:
                try:
                    self.client.delete(f"bm25:{ws}")
                except Exception:
                    pass
            self.client.close()
        finally:
            # Guarantee restoration of original application settings
            settings.REDIS_URL = self.orig_redis_url

    def test_saving_chunks_with_source_id_metadata(self):
        """
        Verify chunks saved to Redis persist source_id alongside chunk_id and text.
        Directly inspects the raw Redis JSON string on port 6380.
        """
        chunks = [
            {"chunk_id": "c1", "text": "PostgreSQL indexing guide", "source_id": "src-docs"},
            {"chunk_id": "c2", "text": "Redis clustering setup", "source_id": "src-docs"},
        ]
        save_index_to_redis(self.workspace_id, chunks)

        # 1. Read raw string directly from Redis
        raw = self.client.get(f"bm25:{self.workspace_id}")
        self.assertIsNotNone(raw, "Expected key to exist in Redis on port 6380")
        stored_list = json.loads(raw.decode("utf-8"))

        self.assertEqual(len(stored_list), 2)
        for item in stored_list:
            self.assertIn("source_id", item)
            self.assertEqual(item["source_id"], "src-docs")
            self.assertIn("chunk_id", item)
            self.assertIn("text", item)

        # 2. Verify load_index_from_redis parses source_id
        loaded = load_index_from_redis(self.workspace_id)
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0]["source_id"], "src-docs")
        self.assertEqual(loaded[1]["source_id"], "src-docs")

    def test_searching_across_multiple_sources_in_one_workspace(self):
        """
        Verify multiple sources coexist in one workspace and can be searched together.
        """
        src_a = [
            {"chunk_id": "a1", "text": "PostgreSQL relational query planner", "source_id": "src-A"},
            {"chunk_id": "a2", "text": "PostgreSQL write ahead log WAL", "source_id": "src-A"},
        ]
        src_b = [
            {"chunk_id": "b1", "text": "Redis in-memory cache TTL eviction", "source_id": "src-B"},
            {"chunk_id": "b2", "text": "Redis pub sub messaging system", "source_id": "src-B"},
            {"chunk_id": "b3", "text": "Redis replication and sentinel", "source_id": "src-B"},
        ]
        save_index_to_redis(self.workspace_id, src_a)
        save_index_to_redis(self.workspace_id, src_b)

        loaded = load_index_from_redis(self.workspace_id)
        self.assertEqual(len(loaded), 5)
        sids = {c["source_id"] for c in loaded}
        self.assertEqual(sids, {"src-A", "src-B"})

        # Search across all sources for 'redis'
        res_redis = asyncio.run(sparse_search("redis", self.workspace_id, top_k=10, source_ids=None))
        self.assertGreaterEqual(len(res_redis), 1)
        self.assertEqual(res_redis[0]["source_id"], "src-B")

        # Search across all sources for 'postgresql'
        res_pg = asyncio.run(sparse_search("postgresql", self.workspace_id, top_k=10, source_ids=None))
        self.assertGreaterEqual(len(res_pg), 1)
        self.assertEqual(res_pg[0]["source_id"], "src-A")

    def test_filtering_search_results_by_source_id(self):
        """
        Verify sparse_search filters results exclusively to the requested source_ids.
        """
        src_a = [
            {"chunk_id": "a1", "text": "Database ACID transactions and locking", "source_id": "src-A"},
            {"chunk_id": "a2", "text": "Database indexing optimization", "source_id": "src-A"},
        ]
        src_b = [
            {"chunk_id": "b1", "text": "Database cache layer memory storage", "source_id": "src-B"},
            {"chunk_id": "b2", "text": "Database key-value pairs TTL", "source_id": "src-B"},
            {"chunk_id": "b3", "text": "Database persistence snapshots", "source_id": "src-B"},
        ]
        save_index_to_redis(self.workspace_id, src_a)
        save_index_to_redis(self.workspace_id, src_b)

        # Filter strictly to src-A
        res_a = asyncio.run(sparse_search("database", self.workspace_id, top_k=10, source_ids=["src-A"]))
        self.assertGreaterEqual(len(res_a), 1)
        for r in res_a:
            self.assertEqual(r["source_id"], "src-A")
            self.assertNotEqual(r["source_id"], "src-B")

        # Filter strictly to src-B
        res_b = asyncio.run(sparse_search("database", self.workspace_id, top_k=10, source_ids=["src-B"]))
        self.assertGreaterEqual(len(res_b), 1)
        for r in res_b:
            self.assertEqual(r["source_id"], "src-B")
            self.assertNotEqual(r["source_id"], "src-A")

    def test_reingest_source_without_duplicating_chunks(self):
        """
        Verify re-ingesting a source updates existing chunks and removes obsolete chunks without duplication.
        """
        initial_chunks = [
            {"chunk_id": "c1", "text": "Initial version of chunk 1", "source_id": "src-X"},
            {"chunk_id": "c2", "text": "Initial version of chunk 2", "source_id": "src-X"},
        ]
        save_index_to_redis(self.workspace_id, initial_chunks)
        self.assertEqual(len(load_index_from_redis(self.workspace_id)), 2)

        # Re-ingest: c1 is updated, c2 is omitted (deleted), c3 is newly added
        updated_chunks = [
            {"chunk_id": "c1", "text": "Updated revised text for chunk 1", "source_id": "src-X"},
            {"chunk_id": "c3", "text": "Newly added chunk 3", "source_id": "src-X"},
        ]
        save_index_to_redis(self.workspace_id, updated_chunks)

        loaded = load_index_from_redis(self.workspace_id)
        self.assertEqual(len(loaded), 2)

        chunk_map = {c["chunk_id"]: c for c in loaded}
        self.assertIn("c1", chunk_map)
        self.assertEqual(chunk_map["c1"]["text"], "Updated revised text for chunk 1")
        self.assertNotIn("c2", chunk_map, "Obsolete chunk c2 was not cleaned up upon source re-ingestion")
        self.assertIn("c3", chunk_map)

    def test_preserving_other_sources_when_one_source_reingested(self):
        """
        Verify re-ingesting Source 1 leaves Source 2 and Source 3 completely untouched.
        """
        src_1 = [{"chunk_id": "s1_c1", "text": "Source 1 text", "source_id": "src-1"}]
        src_2 = [
            {"chunk_id": "s2_c1", "text": "Source 2 text 1", "source_id": "src-2"},
            {"chunk_id": "s2_c2", "text": "Source 2 text 2", "source_id": "src-2"},
        ]
        src_3 = [{"chunk_id": "s3_c1", "text": "Source 3 text", "source_id": "src-3"}]

        save_index_to_redis(self.workspace_id, src_1)
        save_index_to_redis(self.workspace_id, src_2)
        save_index_to_redis(self.workspace_id, src_3)
        self.assertEqual(len(load_index_from_redis(self.workspace_id)), 4)

        # Re-ingest Source 2 with new text
        src_2_revised = [
            {"chunk_id": "s2_c1", "text": "Source 2 brand new text 1", "source_id": "src-2"},
            {"chunk_id": "s2_c3", "text": "Source 2 brand new text 3", "source_id": "src-2"},
        ]
        save_index_to_redis(self.workspace_id, src_2_revised)

        loaded = load_index_from_redis(self.workspace_id)
        self.assertEqual(len(loaded), 4)

        chunk_map = {c["chunk_id"]: c for c in loaded}
        # src-1 untouched
        self.assertIn("s1_c1", chunk_map)
        self.assertEqual(chunk_map["s1_c1"]["text"], "Source 1 text")
        # src-3 untouched
        self.assertIn("s3_c1", chunk_map)
        self.assertEqual(chunk_map["s3_c1"]["text"], "Source 3 text")
        # src-2 updated
        self.assertEqual(chunk_map["s2_c1"]["text"], "Source 2 brand new text 1")
        self.assertNotIn("s2_c2", chunk_map)
        self.assertIn("s2_c3", chunk_map)

    def test_deleting_one_source_without_affecting_other_sources(self):
        """
        Verify delete_source_from_redis removes only the specified source.
        """
        save_index_to_redis(self.workspace_id, [{"chunk_id": "p1", "text": "Doc P", "source_id": "src-P"}])
        save_index_to_redis(self.workspace_id, [{"chunk_id": "q1", "text": "Doc Q", "source_id": "src-Q"}])
        save_index_to_redis(self.workspace_id, [{"chunk_id": "r1", "text": "Doc R", "source_id": "src-R"}])

        self.assertEqual(len(load_index_from_redis(self.workspace_id)), 3)

        delete_source_from_redis(self.workspace_id, "src-Q")

        loaded = load_index_from_redis(self.workspace_id)
        self.assertEqual(len(loaded), 2)
        sids = {c["source_id"] for c in loaded}
        self.assertEqual(sids, {"src-P", "src-R"})

    def test_workspace_isolation_between_different_workspaces(self):
        """
        Verify documents in workspace A are never accessible or visible in workspace B.
        """
        ws_a = f"ws-a-{uuid.uuid4().hex[:8]}"
        ws_b = f"ws-b-{uuid.uuid4().hex[:8]}"
        self.created_workspaces.extend([ws_a, ws_b])

        save_index_to_redis(ws_a, [
            {"chunk_id": "a_conf", "text": "Classified confidential security parameters", "source_id": "src-a"}
        ])
        save_index_to_redis(ws_b, [
            {"chunk_id": "b_pub", "text": "Public company overview", "source_id": "src-b"}
        ])

        # Search ws_b for confidential terms
        res_in_b = asyncio.run(sparse_search("classified confidential", ws_b, top_k=10))
        # Ensure a_conf is NOT in ws_b results
        self.assertNotIn("a_conf", [r["chunk_id"] for r in res_in_b])

        # Verify Redis keys are separate
        self.assertTrue(self.client.exists(f"bm25:{ws_a}"))
        self.assertTrue(self.client.exists(f"bm25:{ws_b}"))

        # Clean up
        self.client.delete(f"bm25:{ws_a}")
        self.client.delete(f"bm25:{ws_b}")

    def test_concurrent_updates_using_separate_redis_connections(self):
        """
        Verify concurrent writes to the same workspace from multiple threads,
        each using its own real Redis connection to port 6380, successfully resolve
        via Redis WATCH/MULTI/EXEC with ZERO data loss.
        Synchronized using threading.Barrier to maximize write contention.
        Repeated 3 times with unique workspace IDs.
        """
        rounds = 3
        num_workers = 6
        chunks_per_worker = 2

        for r_idx in range(rounds):
            test_ws = f"ws-conc-real-{uuid.uuid4().hex[:8]}"
            self.created_workspaces.append(test_ws)
            expected_total = num_workers * chunks_per_worker
            barrier = threading.Barrier(num_workers)

            def worker_task(worker_id: int):
                # Each concurrent worker uses an independent actual Redis client
                worker_client = redis.from_url(TEST_REDIS_URL)
                try:
                    sid = f"worker-src-{worker_id}"
                    chunks = [
                        {
                            "chunk_id": f"w{worker_id}_c{c_idx}",
                            "text": f"Worker {worker_id} chunk {c_idx} data payload",
                            "source_id": sid,
                        }
                        for c_idx in range(chunks_per_worker)
                    ]
                    # Synchronize all threads at barrier before executing save to ensure true concurrency
                    barrier.wait(timeout=10)
                    save_index_to_redis(test_ws, chunks, client=worker_client)
                finally:
                    worker_client.close()

            with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
                futures = [executor.submit(worker_task, i) for i in range(num_workers)]
                for f in concurrent.futures.as_completed(futures):
                    f.result()  # Re-raise exceptions if any

            loaded = load_index_from_redis(test_ws)
            self.assertEqual(
                len(loaded),
                expected_total,
                f"Round {r_idx}: expected {expected_total} chunks, got {len(loaded)}",
            )

            loaded_sids = {c["source_id"] for c in loaded}
            expected_sids = {f"worker-src-{i}" for i in range(num_workers)}
            self.assertEqual(loaded_sids, expected_sids)

            loaded_cids = [c["chunk_id"] for c in loaded]
            self.assertEqual(len(loaded_cids), len(set(loaded_cids)), "Duplicate chunk IDs detected!")

            # Clean up round key
            self.client.delete(f"bm25:{test_ws}")


if __name__ == "__main__":
    unittest.main()
