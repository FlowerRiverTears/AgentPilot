import re


def lexical_relevance(query: str, content: str) -> float:
    query_terms = _terms(query)
    if not query_terms:
        return 0.0

    normalized_content = _normalize(content)
    matched = sum(1 for term in query_terms if term in normalized_content)
    return matched / len(query_terms)


def _terms(text: str) -> set[str]:
    normalized = _normalize(text)
    terms: set[str] = set()

    for token in re.findall(r"[a-z0-9]{2,}", normalized):
        terms.add(token)

    for sequence in re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]+", normalized):
        if len(sequence) == 1:
            terms.add(sequence)
            continue
        terms.update(sequence[index : index + 2] for index in range(len(sequence) - 1))
        if len(sequence) >= 3:
            terms.update(sequence[index : index + 3] for index in range(len(sequence) - 2))

    return {term for term in terms if len(term) >= 2}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", text.lower())
