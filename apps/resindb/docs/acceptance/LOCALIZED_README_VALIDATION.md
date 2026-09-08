# Localized README validation

The Chinese and English design editions, localized SVGs, translation resources and scientific-figure contracts passed the repository checks below on the exact publishing tree:

- `validate:i18n-visuals`;
- `validate:scientific-ui`;
- ESLint;
- TypeScript;
- isolated unit tests;
- production build;
- strict UTF-8, mojibake and forbidden-control-character scanning across `README.md`, `README.zh-CN.md` and `README.en.md`;
- local-image discovery for both Markdown image syntax and HTML `<img src="…">` syntax;
- SVG `viewBox`, accessible `title`/`desc`, CJK font fallback, local-path integrity and active-script rejection;
- renderer-portability checks using Noto CJK and librsvg after removal of SVG2 shadow filters that could hide grouped cards in non-browser renderers.

The checks validate software documentation and rendering contracts only. They do not certify resin grades, experiments, force fields or industrial release decisions.
