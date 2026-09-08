import { describe, expect, it } from 'vitest';

import { auditBytes, normalizeBytes } from '../../scripts/validate-repository-unicode.mjs';

const encode = (text) => Buffer.from(text, 'utf8');
const token = (...values) => String.fromCodePoint(...values);

describe('repository Unicode integrity', () => {
  it('accepts clean NFC UTF-8 with one terminal LF', () => {
    expect(auditBytes('clean.md', encode('安全 scientific text\n'))).toEqual([]);
  });

  it('fails replacement characters and mojibake without literal bad fixtures', () => {
    const replacement = auditBytes('replacement.md', encode(`bad ${token(0xfffd)} text\n`));
    const mojibake = auditBytes(
      'mojibake.md',
      encode(`bad ${token(0x951f, 0x65a4, 0x62f7)} text\n`),
    );
    expect(replacement.some((row) => row.category === 'replacement_character')).toBe(true);
    expect(mojibake.some((row) => row.category === 'mojibake')).toBe(true);
  });

  it('fails invalid UTF-8, BOM, CRLF, controls, NFC drift and terminal LF defects', () => {
    const cases = [
      ['invalid.txt', Buffer.from([0xc3, 0x28, 0x0a]), 'invalid_utf8'],
      ['bom.md', Buffer.concat([Buffer.from([0xef, 0xbb, 0xbf]), encode('text\n')]), 'bom'],
      ['crlf.txt', encode('text\r\n'), 'line_endings'],
      ['control.txt', Buffer.concat([encode('bad'), Buffer.from([0x00]), encode('value\n')]), 'control_character'],
      ['nfc.md', encode(`caf${token(0x65, 0x0301)}\n`), 'nfc'],
      ['missing.md', encode('text'), 'terminal_lf'],
      ['double.md', encode('text\n\n'), 'terminal_lf'],
    ];
    for (const [name, bytes, category] of cases) {
      expect(auditBytes(name, bytes).some((row) => row.category === category), `${name}:${category}`).toBe(true);
    }
  });

  it('normalizes only mechanical text properties', () => {
    const raw = Buffer.concat([
      Buffer.from([0xef, 0xbb, 0xbf]),
      encode(`caf${token(0x65, 0x0301)}\r\n\r\n`),
    ]);
    const normalized = normalizeBytes(raw);
    expect(normalized.toString('utf8')).toBe(`caf${token(0x00e9)}\n`);
    expect(auditBytes('normalized.md', normalized)).toEqual([]);

    const semanticCorruption = normalizeBytes(encode(`bad ${token(0xfffd)} text\r\n`));
    expect(
      auditBytes('semantic.md', semanticCorruption).some(
        (row) => row.category === 'replacement_character',
      ),
    ).toBe(true);
  });
});
