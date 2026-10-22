import { loadAccountsFromJson, saveAccountsToJson, AccountRecord } from './utils/accountLoader';

/*
 * Simple wizard to add/update an API key inside accounts.json
 * Usage: npx tsx scripts/addApiKey.ts <accountLabel|number> <apiKey> <apiSecret>
 */

function usage() {
  console.log('Usage: npx tsx scripts/addApiKey.ts <accountLabel|number> <apiKey> <apiSecret>');
  console.log('Examples:');
  console.log('  npx tsx scripts/addApiKey.ts quackers-4 <key> <secret>');
  console.log('  npx tsx scripts/addApiKey.ts 4 <key> <secret>  # becomes quackers-4');
}

async function main() {
  const [identifier, apiKey, apiSecret] = process.argv.slice(2);
  if (!identifier || !apiKey || !apiSecret) {
    usage();
    process.exit(1);
  }

  const numericId = Number(identifier);
  const normalizedName = Number.isInteger(numericId) && numericId > 0
    ? `quackers-${numericId}`
    : identifier.trim();

  if (!normalizedName) {
    console.error('Account label cannot be empty.');
    process.exit(1);
  }

  const accounts = loadAccountsFromJson();
  let updated = false;

  const sanitizedAccounts: AccountRecord[] = accounts.map(acc => ({
    name: acc.name,
    apiKey: acc.apiKey,
    apiSecret: acc.apiSecret,
  }));

  for (let i = 0; i < sanitizedAccounts.length; i++) {
    if (sanitizedAccounts[i].name === normalizedName) {
      sanitizedAccounts[i] = {
        name: normalizedName,
        apiKey,
        apiSecret,
      };
      updated = true;
      break;
    }
  }

  if (!updated) {
    sanitizedAccounts.push({ name: normalizedName, apiKey, apiSecret });
  }

  saveAccountsToJson(sanitizedAccounts);

  if (updated) {
    console.log(`✅ Updated API key for ${normalizedName} in accounts.json`);
  } else {
    console.log(`✅ Added ${normalizedName} to accounts.json`);
  }

  console.log('You can now run:');
  console.log('CONFIRM_LIVE_TRADING=yes npx tsx scripts/multiAccountBeast.ts');
}

main();
