/**
 * InvestigationForm component tests.
 * Uses @testing-library/react — no real API calls.
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import InvestigationForm from '@/components/InvestigationForm';

const noop = jest.fn().mockResolvedValue(undefined);

describe('InvestigationForm', () => {
  beforeEach(() => noop.mockClear());

  it('renders required fields', () => {
    render(<InvestigationForm onSubmit={noop} isLoading={false} />);
    expect(screen.getByPlaceholderText(/Problem Title/i)).toBeTruthy();
    expect(screen.getByText(/Start Investigation/i)).toBeTruthy();
    expect(screen.getByText(/Technology/i)).toBeTruthy();
    expect(screen.getByText(/Environment/i)).toBeTruthy();
  });

  it('disables submit when fields are empty', () => {
    render(<InvestigationForm onSubmit={noop} isLoading={false} />);
    const btn = screen.getByRole('button', { name: /Start Investigation/i });
    expect(btn).toBeDisabled();
  });

  it('calls onSubmit with correct data', async () => {
    render(<InvestigationForm onSubmit={noop} isLoading={false} />);
    await userEvent.type(
      screen.getByPlaceholderText(/e\.g\. Kubernetes/i),
      'Pod CrashLoopBackOff'
    );
    await userEvent.type(
      screen.getByPlaceholderText(/Describe the issue/i),
      'Pod keeps restarting with OOMKilled error'
    );
    const btn = screen.getByRole('button', { name: /Start Investigation/i });
    fireEvent.click(btn);
    await waitFor(() => expect(noop).toHaveBeenCalledTimes(1));
    const arg = noop.mock.calls[0][0];
    expect(arg.problem_title).toBe('Pod CrashLoopBackOff');
    expect(arg.problem_description).toContain('OOMKilled');
  });

  it('shows loading spinner when isLoading=true', () => {
    render(<InvestigationForm onSubmit={noop} isLoading={true} />);
    // Button should be disabled and show spinner svg
    const btn = screen.getByRole('button', { name: /investigating/i });
    expect(btn).toBeDisabled();
  });
});
