import DOMPurify from "dompurify";
import { marked } from "marked";

export interface AnswerPart {
  type: "text" | "code" | "mermaid";
  content: string;
  language?: string;
  html?: string;
}

export function cleanAnswerText(text: string) {
  return text
    .replace(/^\s{0,3}#{1,6}\s*/gm, "")
    .replace(/^\s{0,3}(-{3,}|\*{3,}|_{3,})\s*$/gm, "")
    .replace(/^\s{0,3}>\s?/gm, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export function renderMarkdown(text: string): string {
  try {
    const raw = marked.parse(text, { async: false }) as string;
    return DOMPurify.sanitize(raw);
  } catch {
    return text;
  }
}

export function parseAnswerParts(text: string): AnswerPart[] {
  const parts: AnswerPart[] = [];
  const blockPattern = /```(\w+)?\n?([\s\S]*?)```/g;
  let cursor = 0;
  let match: RegExpExecArray | null;

  while ((match = blockPattern.exec(text))) {
    const plain = text.slice(cursor, match.index);
    if (plain.trim()) {
      parts.push({ type: "text", content: plain, html: renderMarkdown(plain) });
    }
    const language = match[1] || "";
    const codeContent = match[2].trim();
    if (language.toLowerCase() === "mermaid") {
      parts.push({ type: "mermaid", content: codeContent, language: "mermaid" });
    } else {
      parts.push({ type: "code", language, content: codeContent });
    }
    cursor = match.index + match[0].length;
  }

  const tail = text.slice(cursor);
  if (tail.trim()) {
    parts.push({ type: "text", content: tail, html: renderMarkdown(tail) });
  }

  return parts.length ? parts : [{ type: "text", content: text, html: renderMarkdown(text) }];
}

export function splitThinking(answer: string) {
  const match = answer.match(/<think([\s\S]*?)<\/think>/i);
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
