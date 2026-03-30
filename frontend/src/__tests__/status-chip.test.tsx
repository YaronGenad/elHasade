import { describe, it, expect } from 'vitest';
import { screen } from '@testing-library/react';
import { StatusChip } from '../components/StatusChip';
import { renderWithProviders } from './helpers';

describe('StatusChip', () => {
  it('renders pending status with correct label', () => {
    renderWithProviders(<StatusChip status="pending" />);
    expect(screen.getByText(/ממתין/)).toBeInTheDocument();
  });

  it('renders processing status with correct label', () => {
    renderWithProviders(<StatusChip status="processing" />);
    expect(screen.getByText(/מעבד/)).toBeInTheDocument();
  });

  it('renders completed status with correct label', () => {
    renderWithProviders(<StatusChip status="completed" />);
    expect(screen.getByText(/הושלם/)).toBeInTheDocument();
  });

  it('renders failed status with correct label', () => {
    renderWithProviders(<StatusChip status="failed" />);
    expect(screen.getByText(/נכשל/)).toBeInTheDocument();
  });

  it('renders unknown status using the raw status string', () => {
    renderWithProviders(<StatusChip status="cancelled" />);
    expect(screen.getByText('cancelled')).toBeInTheDocument();
  });

  it('renders with small size by default', () => {
    renderWithProviders(<StatusChip status="completed" />);
    const chip = screen.getByText(/הושלם/).closest('.MuiChip-root');
    expect(chip).toHaveClass('MuiChip-sizeSmall');
  });

  it('renders with medium size when specified', () => {
    renderWithProviders(<StatusChip status="completed" size="medium" />);
    const chip = screen.getByText(/הושלם/).closest('.MuiChip-root');
    expect(chip).toHaveClass('MuiChip-sizeMedium');
  });
});
