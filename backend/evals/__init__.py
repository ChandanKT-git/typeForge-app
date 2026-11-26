"""TypeForge LLM Evaluation Suite (Phase 3).

Evaluates the TypeForge AI pipeline across four core dimensions:
  1. Format Compliance (test_format_compliance.py):
     100% Pydantic schema adherence across all endpoints and domains.
  2. Content Quality (test_content_quality.py):
     Printable-ASCII safety, target word-count adherence, sentence completeness,
     and Flesch-Kincaid readability.
  3. Factual Accuracy (test_factual_accuracy.py):
     LLM-as-Judge rubric scoring (1-5 scale) for technical CS accuracy, plus
     negative control tests to verify judge discrimination on hallucinations.
  4. RAG Grounding (test_rag_grounding.py):
     Faithfulness of `/api/documents/generate-drill` outputs to the retrieved
     document chunks without hallucinating external topics.
"""
