# Frontend structure

- `src/api/client.ts`: central API client and error handling
- `src/auth/AuthContext.tsx`: login state, token persistence and role checks
- `src/components/`: shared UI such as header and login panel
- `src/features/general/`: public/general application area
- `src/features/recipes/`: authenticated recipe entry and image upload
- `src/features/admin/`: admin/super-admin user administration
- `src/types.ts`: shared API/domain types

The navigation hides protected areas based on the authenticated user. The backend must still enforce authentication and authorization for every protected endpoint; hiding frontend components is not a security boundary.
