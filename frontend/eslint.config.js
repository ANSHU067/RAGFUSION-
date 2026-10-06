import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{js,jsx}'],
    extends: [
      js.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: { ...globals.browser, ...globals.node },
      parserOptions: { ecmaFeatures: { jsx: true } },
    },
    rules: {
      // shadcn/ui co-locates component helpers with their components.
      'react-refresh/only-export-components': 'off',
      // React 19's JSX transform does not require React to be referenced directly.
      'no-unused-vars': ['error', { varsIgnorePattern: '^React$' }],
      // The provider intentionally synchronizes its derived browser-theme state.
      'react-hooks/set-state-in-effect': 'off',
    },
  },
])
