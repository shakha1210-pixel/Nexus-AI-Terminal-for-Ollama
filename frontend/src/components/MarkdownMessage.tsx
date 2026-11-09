import { Fragment, type ReactNode } from "react";

type MarkdownMessageProps = { content: string };

function renderInline(source: string, keyPrefix: string): ReactNode[] {
  const pattern = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*|\[([^\]]+)\]\((https?:\/\/[^\s)]+)\))/g;
  const nodes: ReactNode[] = [];
  let cursor = 0;
  let index = 0;

  for (const match of source.matchAll(pattern)) {
    const start = match.index ?? 0;
    if (start > cursor) nodes.push(source.slice(cursor, start));
    const token = match[0];
    if (token.startsWith("`")) {
      nodes.push(<code key={`${keyPrefix}-${index++}`}>{token.slice(1, -1)}</code>);
    } else if (token.startsWith("**")) {
      nodes.push(<strong key={`${keyPrefix}-${index++}`}>{token.slice(2, -2)}</strong>);
    } else if (token.startsWith("*")) {
      nodes.push(<em key={`${keyPrefix}-${index++}`}>{token.slice(1, -1)}</em>);
    } else if (match[2] && match[3]) {
      nodes.push(
        <a key={`${keyPrefix}-${index++}`} href={match[3]} target="_blank" rel="noopener noreferrer">
          {match[2]}
        </a>,
      );
    }
    cursor = start + token.length;
  }

  if (cursor < source.length) nodes.push(source.slice(cursor));
  return nodes;
}

export default function MarkdownMessage({ content }: MarkdownMessageProps) {
  const lines = content.replace(/\r\n?/g, "\n").split("\n");
  const blocks: ReactNode[] = [];
  let paragraph: string[] = [];
  let listItems: string[] = [];
  let listType: "ul" | "ol" | null = null;

  const flushParagraph = () => {
    if (!paragraph.length) return;
    blocks.push(
      <p key={`paragraph-${blocks.length}`}>
        {paragraph.map((line, index) => (
          <Fragment key={index}>{index > 0 && <br />}{renderInline(line, `p-${blocks.length}-${index}`)}</Fragment>
        ))}
      </p>,
    );
    paragraph = [];
  };

  const flushList = () => {
    if (!listItems.length || !listType) return;
    const Tag = listType;
    blocks.push(
      <Tag key={`list-${blocks.length}`}>
        {listItems.map((item, index) => <li key={index}>{renderInline(item, `l-${blocks.length}-${index}`)}</li>)}
      </Tag>,
    );
    listItems = [];
    listType = null;
  };

  const flushText = () => {
    flushParagraph();
    flushList();
  };

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    const fence = line.match(/^\s*```([\w.+-]*)\s*$/);
    if (fence) {
      flushText();
      const codeLines: string[] = [];
      while (index + 1 < lines.length && !/^\s*```\s*$/.test(lines[index + 1])) {
        codeLines.push(lines[index + 1]);
        index += 1;
      }
      if (index + 1 < lines.length) index += 1;
      const language = fence[1];
      blocks.push(
        <pre key={`code-${blocks.length}`}>
          <code className={language ? `language-${language}` : undefined}>{codeLines.join("\n")}</code>
        </pre>,
      );
      continue;
    }

    if (!line.trim()) {
      flushText();
      continue;
    }

    const heading = line.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      flushText();
      const level = heading[1].length;
      const text = renderInline(heading[2], `heading-${blocks.length}`);
      if (level === 1) blocks.push(<h3 key={blocks.length}>{text}</h3>);
      else if (level === 2) blocks.push(<h4 key={blocks.length}>{text}</h4>);
      else blocks.push(<h5 key={blocks.length}>{text}</h5>);
      continue;
    }

    const unordered = line.match(/^\s*[-*+]\s+(.+)$/);
    const ordered = line.match(/^\s*\d+\.\s+(.+)$/);
    if (unordered || ordered) {
      flushParagraph();
      const nextType = unordered ? "ul" : "ol";
      if (listType && listType !== nextType) flushList();
      listType = nextType;
      listItems.push((unordered ?? ordered)![1]);
      continue;
    }

    const quote = line.match(/^>\s?(.*)$/);
    if (quote) {
      flushText();
      blocks.push(<blockquote key={blocks.length}>{renderInline(quote[1], `quote-${blocks.length}`)}</blockquote>);
      continue;
    }

    if (/^\s*---+\s*$/.test(line)) {
      flushText();
      blocks.push(<hr key={blocks.length} />);
      continue;
    }

    flushList();
    paragraph.push(line);
  }

  flushText();
  return <div className="chat-markdown">{blocks}</div>;
}
