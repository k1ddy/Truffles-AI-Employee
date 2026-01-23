# Console API Contracts v1

This directory contains the **contract-first** specifications for the Truffles Console BFF API.

## Files

| File | Purpose |
|------|---------|
| `openapi.v1.yaml` | OpenAPI 3.1 specification for all Console API endpoints |
| `openapi.generated.yaml` | Generated artifact for drift checks (not canonical) |
| `errors.v1.json` | Error codes registry with HTTP status and UI behavior mappings |

## Usage

### Generate TypeScript Client

```bash
# Using openapi-typescript (recommended)
npx openapi-typescript contracts/console_api/openapi.v1.yaml -o console-web/src/types/api.d.ts

# Or orval for React Query hooks
npx orval --input contracts/console_api/openapi.v1.yaml --output console-web/src/api
```

### Validate API Spec

```bash
npx @redocly/cli lint contracts/console_api/openapi.v1.yaml
```

### Optional Drift Check (Paths/Methods)

```bash
python3 truffles-api/scripts/generate_openapi.py --check
```

### Frontend Error Handling

Import and use error codes for consistent UI behavior:

```typescript
import errorsConfig from '@/contracts/errors.v1.json';

function handleApiError(error: ApiError) {
  const config = errorsConfig.errors[error.code];
  if (!config) return showGenericError(error);
  
  switch (config.ui_behavior.action) {
    case 'redirect_login':
      clearTokens(); router.push('/login'); break;
    case 'refresh_item':
      queryClient.invalidateQueries(['case', caseId]); break;
    case 'toast':
      toast[config.ui_behavior.toast_type](error.message); break;
    // ... handle other actions
  }
}
```

## Versioning

- **Breaking changes** require a new version file (e.g., `openapi.v2.yaml`)
- Non-breaking additions (new optional fields, new endpoints) can be added to current version
- Error codes follow the same versioning strategy

## Contract Validation (CI)

Add to CI pipeline:

```yaml
- name: Validate OpenAPI
  run: npx @redocly/cli lint contracts/console_api/openapi.v1.yaml

- name: Contract Tests
  run: schemathesis --config-file contracts/console_api/schemathesis.toml run contracts/console_api/openapi.v1.yaml --url http://localhost:8000
```

**Seed overrides**
- `contracts/console_api/schemathesis.toml` provides stable `case_id` / `conversation_id`.
- If they go stale, update both this file and the `example` values in `openapi.v1.yaml`.
