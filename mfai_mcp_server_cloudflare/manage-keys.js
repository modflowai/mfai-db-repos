#!/usr/bin/env node

import crypto from 'crypto';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

// Get __dirname equivalent in ES modules
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Key storage file (gitignored)
const KEY_FILE = path.join(__dirname, '.mcp-keys.json');

// Commands
const command = process.argv[2];

switch (command) {
  case 'generate':
    generateKey();
    break;
  case 'list':
    listKeys();
    break;
  case 'rotate':
    rotateKey();
    break;
  default:
    console.log(`
MCP API Key Manager

Commands:
  node manage-keys.js generate  - Generate a new API key
  node manage-keys.js list      - List all keys (with created dates)
  node manage-keys.js rotate    - Generate new key and archive old one

Example:
  node manage-keys.js generate
    `);
}

function generateKey() {
  const key = crypto.randomBytes(32).toString('hex');
  const keyData = {
    key,
    created: new Date().toISOString(),
    environment: process.argv[3] || 'production'
  };
  
  // Save to file
  const keys = loadKeys();
  keys.active = keyData;
  keys.history = keys.history || [];
  saveKeys(keys);
  
  console.log(`
Generated new API key:
${key}

To set in production:
npx wrangler secret put MCP_API_KEY
(then paste the key above)

To set locally:
Add to .dev.vars:
MCP_API_KEY=${key}

To use in tests:
MCP_API_KEY=${key} node test-prod.js
  `);
}

function listKeys() {
  const keys = loadKeys();
  
  console.log('\nActive Key:');
  if (keys.active) {
    console.log(`  Created: ${keys.active.created}`);
    console.log(`  Environment: ${keys.active.environment}`);
    console.log(`  Key: ${keys.active.key.substring(0, 8)}...${keys.active.key.substring(56)}`);
  } else {
    console.log('  No active key');
  }
  
  if (keys.history && keys.history.length > 0) {
    console.log('\nKey History:');
    keys.history.forEach((k, i) => {
      console.log(`  ${i + 1}. ${k.created} - ${k.key.substring(0, 8)}...`);
    });
  }
}

function rotateKey() {
  const keys = loadKeys();
  
  // Archive current key
  if (keys.active) {
    keys.history = keys.history || [];
    keys.history.push({
      ...keys.active,
      rotated: new Date().toISOString()
    });
  }
  
  // Generate new key
  generateKey();
  
  console.log('\n⚠️  Remember to update all clients with the new key!');
}

function loadKeys() {
  try {
    return JSON.parse(fs.readFileSync(KEY_FILE, 'utf8'));
  } catch (e) {
    return {};
  }
}

function saveKeys(keys) {
  fs.writeFileSync(KEY_FILE, JSON.stringify(keys, null, 2));
}