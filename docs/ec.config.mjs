// pgtail and pgtail-log blocks are colored by pgtail itself: scripts/Highlight-Docs.cs runs its formatter, highlighters,
// and themes over them and writes the spans to src/generated/pgtail-tokens.json, and this plugin lays those on the
// rendered lines, the dark theme's on the dark ground and the light theme's on the light one. Shiki never sees them.
import { definePlugin, InlineStyleAnnotation } from '@expressive-code/core';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';

const map = JSON.parse(readFileSync(new URL('./src/generated/pgtail-tokens.json', import.meta.url), 'utf8'));
const terminalLanguages = new Set(['pgtail', 'pgtail-log']);

// The block's text as the generator keys it: its lines, trailing blank lines dropped, joined by newlines.
const key = (code) => {
  const lines = code.split('\n');
  while (lines.length > 0 && lines[lines.length - 1].trim().length === 0) lines.pop();
  return createHash('sha256').update(lines.join('\n'), 'utf8').digest('hex');
};

const terminalColors = definePlugin({
  name: 'pgtail-terminal',
  hooks: {
    postprocessAnalyzedCode: ({ codeBlock, styleVariants }) => {
      if (!terminalLanguages.has(codeBlock.language)) return;
      const block = map.blocks[key(codeBlock.code)];
      if (!block) return;
      codeBlock.getLines().forEach((line, i) => {
        for (const span of block.lines[i] ?? []) {
          const inlineRange = { columnStart: span.start, columnEnd: span.start + span.length };
          styleVariants.forEach((variant, styleVariantIndex) => {
            const light = variant.theme.type === 'light';
            line.addAnnotation(
              new InlineStyleAnnotation({
                inlineRange,
                color: light ? span.light : span.dark,
                bgColor: light ? span.lightBackground : span.darkBackground,
                bold: span.bold,
                italic: span.italic,
                underline: span.underline,
                styleVariantIndex,
              }),
            );
          });
        }
      });
    },
  },
});

export default {
  // These languages exist so the blocks are not reported as unknown; they carry no grammar, since the colors come
  // from the plugin.
  shiki: {
    langs: [
      { name: 'pgtail', scopeName: 'source.pgtail', patterns: [] },
      { name: 'pgtail-log', scopeName: 'source.pgtail-log', patterns: [] },
    ],
  },
  plugins: [terminalColors],
};
