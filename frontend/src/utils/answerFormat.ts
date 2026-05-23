export interface AnswerPart {
  type: "text" | "code";
  content: string;
  language?: string;
}

export function cleanAnswerText(text: string) {
  return text
    .replace(/^\s{0,3}#{1,6}\s*/gm, "")
    .replace(/^\s{0,3}(-{3,}|\*{3,}|_{3,})\s*$/gm, "")
    .replace(/^\s{0,3}>\s?/gm, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export function parseAnswerParts(text: string): AnswerPart[] {
  const parts: AnswerPart[] = [];
  const blockPattern = /```(\w+)?\n?([\s\S]*?)```/g;
  let cursor = 0;
  let match: RegExpExecArray | null;

  while ((match = blockPattern.exec(text))) {
    const plain = cleanAnswerText(text.slice(cursor, match.index));
    if (plain) {
      parts.push({ type: "text", content: plain });
    }
    parts.push({
      type: "code",
      language: match[1] || "",
      content: match[2].trim()
    });
    cursor = match.index + match[0].length;
  }

  const tail = cleanAnswerText(text.slice(cursor));
  if (tail) {
    parts.push({ type: "text", content: tail });
  }

  return parts.length ? parts : [{ type: "text", content: cleanAnswerText(text) }];
}

export function splitThinking(answer: string) {
  const match = answer.match(/<think>([\s\S]*?)<\/think>/i);
  if (!match) {
    const content = cleanAnswerText(answer);
    return { content, parts: parseAnswerParts(answer), thinking: "" };
  }

  const withoutThinking = answer.replace(match[0], "");
  return {
    thinking: match[1].trim(),
    content: cleanAnswerText(withoutThinking),
    parts: parseAnswerParts(withoutThinking)
  };
}
