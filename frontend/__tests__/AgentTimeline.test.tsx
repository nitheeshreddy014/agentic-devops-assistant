/**
 * Tests for AgentTimeline — icons, duration, expandable messages.
 */
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import AgentTimeline from '../components/AgentTimeline';
import type { AgentMessage } from '../lib/types';

const MESSAGES: AgentMessage[] = [
  {
    agent: 'Triage Agent', agent_name: 'triage', phase: 'triage',
    status: 'complete', message: 'Issue categorised as kubernetes/network',
    timestamp: '2024-01-01T00:00:00Z', duration_ms: 1234,
  },
  {
    agent: 'Safety Reviewer', agent_name: 'safety_reviewer', phase: 'safety',
    status: 'complete', message: 'All steps verified safe.',
    timestamp: '2024-01-01T00:00:01Z', duration_ms: 456,
  },
];

describe('AgentTimeline', () => {
  test('renders nothing when messages is empty', () => {
    const { container } = render(<AgentTimeline messages={[]} />);
    expect(container.querySelector('ol')).toBeNull();
  });

  test('renders all agent names', () => {
    render(<AgentTimeline messages={MESSAGES} />);
    expect(screen.getByText('Triage Agent')).toBeInTheDocument();
    expect(screen.getByText('Safety Reviewer')).toBeInTheDocument();
  });

  test('renders duration in seconds', () => {
    render(<AgentTimeline messages={MESSAGES} />);
    expect(screen.getByText('1.2s')).toBeInTheDocument();
  });

  test('clicking an agent expands its full message', () => {
    render(<AgentTimeline messages={MESSAGES} />);
    const btn = screen.getAllByRole('button')[0];
    fireEvent.click(btn);
    // message text should now be visible in expanded section
    expect(screen.getAllByText(/Issue categorised as kubernetes\/network/).length).toBeGreaterThan(0);
  });

  test('clicking again collapses the message', () => {
    render(<AgentTimeline messages={MESSAGES} />);
    const btn = screen.getAllByRole('button')[0];
    fireEvent.click(btn); // expand
    fireEvent.click(btn); // collapse
    const expanded = document.querySelector('[aria-expanded="true"]');
    expect(expanded).toBeNull();
  });
});
