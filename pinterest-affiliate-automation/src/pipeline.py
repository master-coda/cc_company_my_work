import time
from datetime import date

from src.models import PostResult
from src.pinterest_client import PinterestAPIError
from src.safety_checker import check_copy_safety, hype_terms_for_language

MAX_PINTEREST_RETRIES = 3
PINTEREST_RETRY_BACKOFF_SECONDS = 2
MAX_COPY_SAFETY_ATTEMPTS = 3

_DISCLOSURE = {"ja": "#PR", "en": "#affiliate"}


class Pipeline:
    def __init__(self, catalog, copy_generator, pinterest_client, run_logger, discord, boards: dict):
        self.catalog = catalog
        self.copy_generator = copy_generator
        self.pinterest_client = pinterest_client
        self.run_logger = run_logger
        self.discord = discord
        self.boards = boards

    def run(self, target_date: date, images: dict, count: int = 3) -> list[PostResult]:
        products = self.catalog.pick_for_date(target_date, count=count)
        results: list[PostResult] = []
        for product in products:
            for language in ("ja", "en"):
                results.append(self._process_one(product, language, images))

        self.run_logger.record_run(target_date, results)

        failures = [r for r in results if r.status in ("failed", "skipped_safety")]
        if failures:
            self.discord.send_embed(
                title="Pinterest自動投稿: エラー発生",
                description=f"{len(failures)}件の投稿に失敗しました",
                color=0xE74C3C,
                fields={f"{r.product_id}_{r.language}": r.detail for r in failures},
            )
        return results

    def _process_one(self, product: dict, language: str, images: dict) -> PostResult:
        board_id = self.boards[language]
        image_bytes = images.get((product["id"], language))
        if image_bytes is None:
            return PostResult(
                product["id"], language, board_id, None, "failed", "image missing for language"
            )

        copy, safety_reasons = self._generate_safe_copy(product, language)
        if copy is None:
            return PostResult(
                product["id"],
                language,
                board_id,
                None,
                "skipped_safety",
                f"failed safety check after {MAX_COPY_SAFETY_ATTEMPTS} attempts: {'; '.join(safety_reasons)}",
            )

        link = product["a8net_link"] if language == "ja" else product["overseas_link"]["url"]

        last_error = ""
        for attempt in range(1, MAX_PINTEREST_RETRIES + 1):
            try:
                pin = self.pinterest_client.create_pin(
                    board_id=board_id,
                    image_bytes=image_bytes,
                    content_type="image/jpeg",
                    title=copy.title,
                    description=copy.description,
                    link=link,
                    alt_text=copy.title,
                )
                return PostResult(product["id"], language, board_id, pin.get("id"), "posted", "ok")
            except PinterestAPIError as e:
                last_error = str(e)
                if attempt < MAX_PINTEREST_RETRIES:
                    time.sleep(PINTEREST_RETRY_BACKOFF_SECONDS)

        return PostResult(
            product["id"],
            language,
            board_id,
            None,
            "failed",
            f"pinterest create_pin failed after {MAX_PINTEREST_RETRIES} attempts: {last_error}",
        )

    def _generate_safe_copy(self, product: dict, language: str):
        product_name = product["name_ja"] if language == "ja" else product["name_en"]
        disclosure = _DISCLOSURE[language]
        hype_terms = hype_terms_for_language(language)

        last_reasons: list[str] = []
        for _ in range(MAX_COPY_SAFETY_ATTEMPTS):
            copy = self.copy_generator.generate(product_name, language)
            check = check_copy_safety(product_name, copy.title, copy.description, disclosure, hype_terms)
            if check.passed:
                return copy, []
            last_reasons = check.reasons

        return None, last_reasons
