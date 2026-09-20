import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const mockUseAuth = vi.fn();

vi.mock('../auth/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

import { SectionUserInfo } from './SectionUserInfo';

describe('SectionUserInfo', () => {
  const logout = vi.fn();
  const onOpenAccountSettings = vi.fn();

  beforeEach(() => {
    logout.mockReset();
    onOpenAccountSettings.mockReset();
    mockUseAuth.mockReturnValue({
      user: {
        username: 'joergu',
        first_name: 'Jörg',
        last_name: 'Unbehaun',
        is_super_admin: true,
      },
      logout,
      mayManageUsers: true,
    });
  });

  it('shows account actions from the user menu', async () => {
    const user = userEvent.setup();
    render(<SectionUserInfo onOpenAccountSettings={onOpenAccountSettings} />);

    await user.click(screen.getByRole('button', { name: /Jörg Unbehaun/i }));
    expect(screen.getByText('Super-Admin')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('menuitem', { name: 'Einstellungen' }));
    expect(onOpenAccountSettings).toHaveBeenCalledWith('profile');

    await user.click(screen.getByRole('button', { name: /Jörg Unbehaun/i }));
    fireEvent.click(screen.getByRole('menuitem', { name: 'Passwort ändern' }));
    expect(onOpenAccountSettings).toHaveBeenCalledWith('password');

    await user.click(screen.getByRole('button', { name: /Jörg Unbehaun/i }));
    fireEvent.click(screen.getByRole('menuitem', { name: 'Abmelden' }));
    expect(logout).toHaveBeenCalledOnce();
  });
});
