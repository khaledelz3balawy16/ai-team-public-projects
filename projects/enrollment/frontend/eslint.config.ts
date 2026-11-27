import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import routeElementPlugin from './eslint-rules/route-element-jsx.js'
import noRawInternalAnchorPlugin from './eslint-rules/no-raw-internal-anchor.js'

const autoImportGlobals = {
  // React
  React: 'CHANGE_ME',
  useState: 'CHANGE_ME',
  useEffect: 'CHANGE_ME',
  useContext: 'CHANGE_ME',
  useReducer: 'CHANGE_ME',
  useCallback: 'CHANGE_ME',
  useMemo: 'CHANGE_ME',
  useRef: 'CHANGE_ME',
  useImperativeHandle: 'CHANGE_ME',
  useLayoutEffect: 'CHANGE_ME',
  useDebugValue: 'CHANGE_ME',
  useDeferredValue: 'CHANGE_ME',
  useId: 'CHANGE_ME',
  useInsertionEffect: 'CHANGE_ME',
  useSyncExternalStore: 'CHANGE_ME',
  useTransition: 'CHANGE_ME',
  startTransition: 'CHANGE_ME',
  lazy: 'CHANGE_ME',
  memo: 'CHANGE_ME',
  forwardRef: 'CHANGE_ME',
  createContext: 'CHANGE_ME',
  createElement: 'CHANGE_ME',
  cloneElement: 'CHANGE_ME',
  isValidElement: 'CHANGE_ME',
  // React Router
  useNavigate: 'CHANGE_ME',
  useLocation: 'CHANGE_ME',
  useParams: 'CHANGE_ME',
  useSearchParams: 'CHANGE_ME',
  Link: 'CHANGE_ME',
  NavLink: 'CHANGE_ME',
  Navigate: 'CHANGE_ME',
  Outlet: 'CHANGE_ME',
  // React i18n
  useTranslation: 'CHANGE_ME',
  Trans: 'CHANGE_ME',
  // Auto-imported component. Declared in vite.config.ts alongside the hooks
  // above; without it here every one of its ~6,500 call sites is a no-undef
  // error and the lint script is unusable as a gate.
  AppIcon: 'CHANGE_ME',
}

export default [
  { ignores: ['dist', 'node_modules'] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ['src/**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2020,
      globals: {
        ...globals.browser,
        ...autoImportGlobals,
        NodeJS: 'CHANGE_ME',
        JSX: 'CHANGE_ME',
        IdleRequestCallback: 'CHANGE_ME',
        AddEventListenerOptions: 'CHANGE_ME',
        RequestCache: 'CHANGE_ME',
        RequestCredentials: 'CHANGE_ME',
        RequestInfo: 'CHANGE_ME',
        RequestInit: 'CHANGE_ME',
        __BASE_PATH__: 'CHANGE_ME',
        __IS_PREVIEW__: 'CHANGE_ME',
        __READDY_PROJECT_ID__: 'CHANGE_ME',
        __READDY_VERSION_ID__: 'CHANGE_ME',
        __READDY_AI_DOMAIN__: 'CHANGE_ME',
      },
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': [
        'warn',
        { allowConstantExport: true },
      ],
      '@typescript-eslint/no-namespace': 'off',
      '@typescript-eslint/no-explicit-any': 'off',
      '@typescript-eslint/no-unused-vars': 'off',
      'no-unused-vars': 'off',
      'no-useless-escape': 'off',
      'prefer-const': 'off',
      'prefer-rest-params': 'off',
      'prefer-spread': 'off',
      'no-unused-expressions': 'off',
      'no-case-declarations': 'off',
      '@typescript-eslint/no-unused-expressions': 'off',
      'no-useless-catch': 'off',
      'no-irregular-whitespace': 'off',
      'no-undef': 'error',
    },
  },
  {
    files: ['src/**/*.{test,spec}.{ts,tsx}'],
    languageOptions: {
      globals: globals.node,
    },
  },
  // Only enforce this rule for the router config file to avoid false positives elsewhere.
  {
    files: ['src/router/config.tsx'],
    plugins: {
      'local-route': routeElementPlugin,
    },
    rules: {
      'local-route/route-element-jsx': 'error',
    },
  },
  // Anywhere a page or component links to an in-app route. Excludes the audit
  // sub-apps, which run their own TanStack router and do not use react-router's
  // <Link>, and the mock data modules, which hold hrefs as plain strings.
  {
    files: ['src/pages/**/*.tsx', 'src/components/**/*.tsx'],
    ignores: ['src/features/audit/**'],
    plugins: {
      'local-nav': noRawInternalAnchorPlugin,
    },
    rules: {
      'local-nav/no-raw-internal-anchor': 'error',
    },
  },
]

