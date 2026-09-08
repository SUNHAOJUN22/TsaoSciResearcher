import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { FeedbackModal, buildFeedbackRecord, redactFeedbackText } from '@/components/modals/FeedbackModal';

describe('feedback diagnostics',()=>{
  beforeEach(()=>{localStorage.clear();vi.restoreAllMocks();});
  it('redacts secrets',()=>{expect(redactFeedbackText('api_key=sk-123456789 password=hunter2')).not.toContain('hunter2');expect(redactFeedbackText('token=abc123')).toContain('[REDACTED]');});
  it('builds useful environment metadata without resin data',()=>{const record=buildFeedbackRecord({type:'bug',severity:'high',module:'analytics',title:'Chart failed',description:'Steps with token=abc123',steps:'Open chart'});expect(record.environment.version).toBe('3.2.0');expect(record.description).not.toContain('abc123');expect(JSON.stringify(record)).not.toContain('PRODUCT_CATALOG');});
  it('validates and saves feedback locally',()=>{render(<FeedbackModal isOpen onClose={()=>{}}/>);fireEvent.change(screen.getByTestId('feedback-title'),{target:{value:'Graph issue'}});fireEvent.change(screen.getByTestId('feedback-description'),{target:{value:'The analysis graph did not update after a valid input.'}});fireEvent.click(screen.getByText('保存本地'));expect(localStorage.getItem('resindb-feedback-queue')).toContain('Graph issue');expect(screen.getByText(/已保存到本地/)).toBeInTheDocument();});
  it('rejects incomplete feedback',()=>{render(<FeedbackModal isOpen onClose={()=>{}}/>);fireEvent.click(screen.getByText('保存本地'));expect(screen.getByText(/至少 10 个字符/)).toBeInTheDocument();});
});
