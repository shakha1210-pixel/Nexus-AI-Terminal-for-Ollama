import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from unittest.mock import patch

from app.services.kaggle_notebook_service import KaggleNotebookError, KaggleNotebookService


class KaggleNotebookServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.service = KaggleNotebookService(data_dir=Path(self.temp.name))

    @patch.dict("os.environ", {"KAGGLE_USERNAME": "test-user", "KAGGLE_KEY": "test-key"})
    @patch("app.services.kaggle_notebook_service.subprocess.run")
    def test_search_parses_csv_and_limits_fields(self, run) -> None:
        run.return_value.stdout = (
            "ref,title,author,lastRunTime,totalVotes\\n"
            "owner/notebook,Useful notebook,owner,2026-11-01,12\\n"
            "../bad,Ignore this,attacker,2026-11-01,999\\n"
        )
        run.return_value.stderr = ""
        run.return_value.returncode = 0

        result = self.service.search("transformer", 2)

        self.assertEqual(result["page"], 2)
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["items"][0]["ref"], "owner/notebook")
        args = run.call_args.args[0]
        self.assertEqual(args[-5:], ["-s", "transformer", "-p", "2", "--csv"])

    def test_search_rejects_short_query_before_running_cli(self) -> None:
        with patch("app.services.kaggle_notebook_service.subprocess.run") as run:
            with self.assertRaises(KaggleNotebookError):
                self.service.search("x")
            run.assert_not_called()

    def test_download_rejects_invalid_reference_before_running_cli(self) -> None:
        with patch("app.services.kaggle_notebook_service.subprocess.run") as run:
            with self.assertRaises(KaggleNotebookError):
                self.service.download("../outside")
            run.assert_not_called()

    @patch.dict("os.environ", {"KAGGLE_USERNAME": "test-user", "KAGGLE_KEY": "test-key"})
    @patch("app.services.kaggle_notebook_service.subprocess.run")
    def test_download_stores_only_valid_ipynb(self, run) -> None:
        def fake_run(command, **kwargs):
            output_dir = Path(command[command.index("-p") + 1])
            (output_dir / "source.ipynb").write_text(
                '{"cells":[],"metadata":{},"nbformat":4,"nbformat_minor":5}',
                encoding="utf-8",
            )
            class Result:
                returncode = 0
                stdout = ""
                stderr = ""
            return Result()

        run.side_effect = fake_run
        result = self.service.download("owner/notebook")

        self.assertEqual(result.name, "owner__notebook.ipynb")
        self.assertTrue(result.is_file())
        self.assertIn('"cells"', result.read_text(encoding="utf-8"))

    def test_concurrent_downloads_use_distinct_staging_files(self) -> None:
        barrier = Barrier(2)
        real_replace = __import__("os").replace
        staged_paths: list[Path] = []

        def fake_run(command, **kwargs):
            output_dir = Path(command[command.index("-p") + 1])
            (output_dir / "source.ipynb").write_text(
                '{"cells":[],"metadata":{},"nbformat":4,"nbformat_minor":5}',
                encoding="utf-8",
            )
            class Result:
                returncode = 0
                stdout = ""
                stderr = ""
            return Result()

        def synchronized_replace(source, destination):
            staged_paths.append(Path(source))
            barrier.wait(timeout=5)
            return real_replace(source, destination)

        self.service._run = fake_run
        with patch("app.services.kaggle_notebook_service.os.replace", side_effect=synchronized_replace):
            with ThreadPoolExecutor(max_workers=2) as executor:
                results = list(executor.map(self.service.download, ["owner/notebook", "owner/notebook"]))

        self.assertEqual(results[0], results[1])
        self.assertTrue(results[0].is_file())
        self.assertEqual(len(staged_paths), 2)
        self.assertNotEqual(staged_paths[0], staged_paths[1])
        self.assertTrue(all(not path.exists() for path in staged_paths))


if __name__ == "__main__":
    unittest.main()
