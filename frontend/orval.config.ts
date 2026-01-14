import { defineConfig } from 'orval';

export default defineConfig({
  api: {
    input: {
      target: '../backend/openapi.json', // FastAPIが生成するOpenAPI仕様
    },
    output: {
      mode: 'tags-split',
      target: './src/api/endpoints',
      schemas: './src/api/model',
      client: 'react-query',
      mock: false,
      override: {
        mutator: {
          path: './src/lib/apiClient.ts',
          name: 'customInstance',
        },
      },
    },
  },
});
