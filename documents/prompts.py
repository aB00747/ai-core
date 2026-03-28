DOCUMENT_SUMMARY_PROMPT = """Summarize the following document content concisely. Focus on key information relevant to a chemical trading business.

Document: {file_name}
Content:
{content}

Provide:
1. A 2-3 sentence summary
2. Key entities mentioned (company names, chemical names, amounts, dates)
3. Document category (invoice, report, safety data sheet, contract, correspondence, other)"""
