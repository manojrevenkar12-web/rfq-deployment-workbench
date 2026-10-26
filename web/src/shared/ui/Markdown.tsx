import type { ReactNode } from "react";

import styles from "./Markdown.module.css";

/**
 * Renders the Markdown the workbench itself writes (the SteerCo pack): headings, paragraphs, bullet lists,
 * pipe tables, **bold** and *italic*. It is not a general Markdown renderer and never renders HTML.
 */
function inline(text: string): ReactNode[] {
  const out: ReactNode[] = [];
  const re = /\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`/g;
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index));
    if (m[1]) out.push(<strong key={m.index}>{m[1]}</strong>);
    else if (m[2]) out.push(<em key={m.index}>{m[2]}</em>);
    else out.push(<code key={m.index}>{m[3]}</code>);
    last = re.lastIndex;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

const cells = (line: string) =>
  line
    .trim()
    .replace(/^\||\|$/g, "")
    .split("|")
    .map((c) => c.trim());

export function Markdown({ source }: { source: string }) {
  const lines = source.split("\n");
  const blocks: ReactNode[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i] ?? "";
    if (!line.trim()) {
      i++;
      continue;
    }
    const heading = /^(#{1,3})\s+(.*)$/.exec(line);
    if (heading) {
      const level = heading[1]?.length ?? 1;
      const text = inline(heading[2] ?? "");
      blocks.push(
        level === 1 ? (
          <h2 key={i}>{text}</h2>
        ) : level === 2 ? (
          <h3 key={i}>{text}</h3>
        ) : (
          <h4 key={i}>{text}</h4>
        ),
      );
      i++;
    } else if (line.trim().startsWith("|")) {
      const rows: string[][] = [];
      while (i < lines.length && (lines[i] ?? "").trim().startsWith("|")) {
        const r = cells(lines[i] ?? "");
        if (!r.every((c) => /^:?-{3,}:?$/.test(c))) rows.push(r);
        i++;
      }
      const [head, ...body] = rows;
      blocks.push(
        <div key={i} className={styles.tableWrap}>
          <table>
            <thead>
              <tr>
                {head?.map((c, k) => (
                  <th key={k}>{inline(c)}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {body.map((r, k) => (
                <tr key={k}>
                  {r.map((c, j) => (
                    <td key={j}>{inline(c)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>,
      );
    } else if (/^\s*[-*]\s+/.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i] ?? "")) {
        items.push((lines[i] ?? "").replace(/^\s*[-*]\s+/, ""));
        i++;
      }
      blocks.push(
        <ul key={i}>
          {items.map((t, k) => (
            <li key={k}>{inline(t)}</li>
          ))}
        </ul>,
      );
    } else {
      const para: string[] = [];
      while (
        i < lines.length &&
        (lines[i] ?? "").trim() &&
        !/^(#{1,3}\s|\s*[-*]\s|\s*\|)/.test(lines[i] ?? "")
      ) {
        para.push((lines[i] ?? "").trim());
        i++;
      }
      blocks.push(<p key={i}>{inline(para.join(" "))}</p>);
    }
  }
  return <div className={styles.doc}>{blocks}</div>;
}
