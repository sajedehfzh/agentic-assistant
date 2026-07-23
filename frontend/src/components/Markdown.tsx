import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface Props {
  children: string | null | undefined;
  className?: string;
}

/**
 * Renders LLM output as GitHub-flavored Markdown so tables, bullet lists,
 * code fences, and bold/italic come through styled instead of as raw
 * `**foo**` / `| col |` characters.
 *
 * External links open in a new tab; everything else uses the global
 * stylesheet (see `.markdown` rules in styles.css).
 */
export default function Markdown({ children, className }: Props) {
  if (!children) return null;
  return (
    <div className={`markdown ${className ?? ''}`.trim()}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ node: _node, ...props }) => (
            <a {...props} target="_blank" rel="noopener noreferrer" />
          ),
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
