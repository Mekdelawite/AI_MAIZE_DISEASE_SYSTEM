import React from 'react';
import { ExtensionAgentActivationPage } from './ExtensionAgentActivationPage';

// Email invitations reuse the secure, expiring password-setup flow. Opening a
// link alone does not activate an account.
export const VerifyExtensionAgentEmailPage: React.FC = () => <ExtensionAgentActivationPage />;
