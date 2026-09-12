/**
 * Tests for the interactive MissingInfoPanel component.
 */
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import MissingInfoPanel from '../components/MissingInfoPanel';

describe('MissingInfoPanel', () => {
  test('renders nothing when missingInfo is empty', () => {
    const { container } = render(<MissingInfoPanel missingInfo={[]} />);
    expect(container.firstChild).toBeNull();
  });

  test('renders each missing info item as a label + input', () => {
    render(<MissingInfoPanel missingInfo={['Kubernetes version', 'Node count']} />);
    expect(screen.getByText(/Kubernetes version/)).toBeInTheDocument();
    expect(screen.getByText(/Node count/)).toBeInTheDocument();
  });

  test('submit button is disabled when no answers filled', () => {
    const onSubmit = jest.fn();
    render(
      <MissingInfoPanel
        missingInfo={['K8s version']}
        onSubmitAnswers={onSubmit}
      />
    );
    const btn = screen.getByRole('button');
    expect(btn).toBeDisabled();
  });

  test('submit button enables when at least one answer is filled', () => {
    const onSubmit = jest.fn();
    render(
      <MissingInfoPanel
        missingInfo={['K8s version']}
        onSubmitAnswers={onSubmit}
      />
    );
    const input = screen.getByPlaceholderText(/Answer for/i);
    fireEvent.change(input, { target: { value: '1.28' } });
    const btn = screen.getByRole('button');
    expect(btn).not.toBeDisabled();
  });

  test('calls onSubmitAnswers with filled answers on click', () => {
    const onSubmit = jest.fn().mockResolvedValue(undefined);
    render(
      <MissingInfoPanel
        missingInfo={['K8s version']}
        onSubmitAnswers={onSubmit}
      />
    );
    fireEvent.change(screen.getByPlaceholderText(/Answer for/i), { target: { value: '1.28' } });
    fireEvent.click(screen.getByRole('button'));
    expect(onSubmit).toHaveBeenCalledWith({ 'K8s version': '1.28' });
  });

  test('shows loading text when isLoading is true', () => {
    render(
      <MissingInfoPanel
        missingInfo={['K8s version']}
        onSubmitAnswers={jest.fn()}
        isLoading={true}
      />
    );
    expect(screen.getByText(/Re-analysing/i)).toBeInTheDocument();
  });
});
