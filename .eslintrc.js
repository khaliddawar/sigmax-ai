module.exports = {
  env: {
    browser: true,
    es2021: true,
    node: true,
    webextensions: true,
    jest: true
  },
  extends: [
    'eslint:recommended',
    'prettier'
  ],
  parserOptions: {
    ecmaVersion: 'latest',
    sourceType: 'module'
  },
  rules: {
    'no-console': ['warn', { allow: ['warn', 'error'] }],
    'no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
    'no-var': 'error',
    'prefer-const': 'error',
    'prefer-arrow-callback': 'error',
    'prefer-template': 'error',
    'object-shorthand': 'error',
    'quotes': ['error', 'single', { avoidEscape: true }],
    'semi': ['error', 'always'],
    'comma-dangle': ['error', 'never'],
    'arrow-parens': ['error', 'always'],
    'no-multiple-empty-lines': ['error', { max: 1 }],
    'eqeqeq': ['error', 'always'],
    'curly': ['error', 'all'],
    'brace-style': ['error', '1tbs'],
    'indent': ['error', 2, { SwitchCase: 1 }],
    'max-len': ['warn', { code: 100, ignoreUrls: true, ignoreStrings: true }]
  },
  overrides: [
    {
      files: ['*.test.js', '*.spec.js'],
      rules: {
        'no-console': 'off'
      }
    }
  ],
  globals: {
    chrome: 'readonly'
  }
};