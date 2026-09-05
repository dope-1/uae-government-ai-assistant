from datetime import UTC, datetime

from app.ingestion.schemas import DocumentChunk
from app.retrieval.postgres_hybrid import _intent_adjustment, _rerank_query


def _chunk(*, source_id: str, source_url: str, text: str) -> DocumentChunk:
    return DocumentChunk(
        id=source_id,
        document_id=f"doc-{source_id}",
        source_id=source_id,
        source_url=source_url,
        authority="Test Authority",
        jurisdiction="Dubai",
        title="Service Details",
        language="en",
        text=text,
        chunk_index=0,
        retrieved_at=datetime(2026, 9, 2, tzinfo=UTC),
    )


def test_procedure_query_expands_only_reranker_terms() -> None:
    expanded = _rerank_query("How do I renew my driving licence in Dubai?")
    assert "eye test" in expanded
    assert "payment" in expanded
    assert "traffic file" in expanded


def test_non_procedure_query_is_not_expanded() -> None:
    query = "What is the UAE Golden Visa?"
    assert _rerank_query(query) == query


def test_procedure_intent_adjustment_prefers_steps_over_directory_noise() -> None:
    query = "How do I renew my driving licence in Dubai?"
    steps = _chunk(
        source_id="dubai_driving_licence_renew_en",
        source_url="https://www.rta.ae/driving-licence",
        text=(
            "Steps Take an eye test. Log in using UAE Pass. Select Renew Driving Licence. "
            "Pay all fines and fees. Receive the licence as a Digital Driving Licence."
        ),
    )
    directory = _chunk(
        source_id="dubai_driving_licence_renew_en",
        source_url="https://www.rta.ae/driving-licence",
        text=(
            "Unicare Medical Centre 04 352 9292 Zulekha Medical Centre 600 524 442 "
            "Al Tadawi Medical Centre 04 203 8888 Apple International Polyclinic 04 422 7533 "
            "for Driving Licence renewal eye tests."
        ),
    )

    assert _intent_adjustment(query, steps) > 0.5
    assert _intent_adjustment(query, directory) < _intent_adjustment(query, steps)


def test_driving_query_demotes_neighbouring_vehicle_service_page() -> None:
    query = "How do I renew my driving licence in Dubai?"
    driver = _chunk(
        source_id="dubai_driving_licence_renew_en",
        source_url="https://www.rta.ae/service-details?serviceId=618",
        text=(
            "Log in using UAE Pass. Select Renewing a Driving Licence from Drivers "
            "Licensing Services."
        ),
    )
    vehicle = _chunk(
        source_id="dubai_vehicle_ownership_renew_en",
        source_url="https://www.rta.ae/service-details?serviceId=582",
        text=(
            "Renew Vehicle Ownership. Steps Log in using UAE Pass and enter Emirates ID "
            "or Driving Licence details."
        ),
    )

    assert _intent_adjustment(query, driver) > 0
    assert _intent_adjustment(query, vehicle) < -0.5


def test_abu_dhabi_driver_source_beats_vehicle_source_for_licence_query() -> None:
    query = "What official Abu Dhabi service handles driving licence renewal?"
    driver = _chunk(
        source_id="abu_dhabi_driver_licensing_en",
        source_url="https://admobility.gov.ae/en/driver-licensing-services",
        text="Driver licensing services include issuing and renewing driving licences.",
    )
    vehicle = _chunk(
        source_id="abu_dhabi_vehicle_licensing_en",
        source_url="https://admobility.gov.ae/en/vehicle-licensing-services",
        text=(
            "These encompass issuing and renewing driving licences, registering and "
            "transferring ownership of vehicles."
        ),
    )

    assert _intent_adjustment(query, driver) > _intent_adjustment(query, vehicle)


def test_non_procedure_intent_adjustment_is_neutral_for_unrelated_source() -> None:
    chunk = _chunk(
        source_id="golden_visa",
        source_url="https://u.ae/golden-visa",
        text="Steps Apply online",
    )
    assert _intent_adjustment("What is the UAE Golden Visa?", chunk) == 0.0
