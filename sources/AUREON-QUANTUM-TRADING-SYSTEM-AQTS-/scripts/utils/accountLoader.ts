import fs from 'fs';
import path from 'path';

export interface AccountRecord {
  name: string;
  apiKey: string;
  apiSecret: string;
}

export function loadAccountsFromJson(): AccountRecord[] {
  const accountsPath = path.resolve(process.cwd(), 'accounts.json');

  if (!fs.existsSync(accountsPath)) {
    console.error('❌ accounts.json not found. Populate it with account credentials.');
    return [];
  }

  try {
    const raw = JSON.parse(fs.readFileSync(accountsPath, 'utf-8'));

    if (!Array.isArray(raw)) {
      console.error('❌ accounts.json must export an array of accounts.');
      return [];
    }

    return raw
      .map((acc: any, idx: number) => ({
        name: typeof acc.name === 'string' && acc.name.trim() ? acc.name.trim() : `account-${idx + 1}`,
        apiKey: acc.apiKey,
        apiSecret: acc.apiSecret,
      }))
      .filter((acc) => typeof acc.apiKey === 'string' && acc.apiKey && typeof acc.apiSecret === 'string' && acc.apiSecret);
  } catch (err) {
    console.error('❌ Failed to parse accounts.json:', err);
    return [];
  }
}

export function saveAccountsToJson(accounts: AccountRecord[]): void {
  const accountsPath = path.resolve(process.cwd(), 'accounts.json');
  fs.writeFileSync(accountsPath, JSON.stringify(accounts, null, 2));
}
