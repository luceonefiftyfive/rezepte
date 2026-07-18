export type Role = 'admin' | 'author' | 'reader';
export type GroupRole = { group_id: string; role: Role };
export type UserPublic = {
  id: string;
  username: string;
  first_name: string;
  last_name: string;
  email: string;
  email_verified: boolean;
  groups: GroupRole[];
  is_super_admin: boolean;
  is_active: boolean;
};
export type TokenResponse = { access_token: string; token_type: string; user: UserPublic };
export type RootResponse = {
  service: string;
  status: string;
  message: string;
  python: string;
  package_manager: string;
};
export type HealthResponse = { status: string; service: string; mode: string };
export type SystemCheckItem = { ok: boolean; endpoint?: string; bucket?: string; error?: string };
export type SystemChecksResponse = {
  api: SystemCheckItem;
  mongo_db: SystemCheckItem;
  s3: SystemCheckItem;
  ok: boolean;
};

export type SystemVersionResponse = {
  version: string;
  git_hash: string;
};

export type Unit =
  | 'g'
  | 'kg'
  | 'ml'
  | 'l'
  | 'tsp'
  | 'tbsp'
  | 'piece'
  | 'pinch'
  | 'bunch'
  | 'clove'
  | 'slice'
  | 'cup'
  | 'as_needed'
  | 'custom';
export type ScalingMode = 'linear' | 'manual' | 'none';
export type RecipeIngredient = {
  ingredient_id?: string | null;
  name: string;
  amount: string | null;
  unit: Unit;
  custom_unit?: string | null;
  preparation?: string | null;
  remarks?: string | null;
  optional: boolean;
  scaling: ScalingMode;
};
export type IngredientSection = {
  id: string;
  name: string | null;
  ingredients: RecipeIngredient[];
};
export type InstructionStep = { id: string; text: string; image_key?: string | null };
export type RecipeTime = {
  preparation_minutes: number | null;
  cooking_minutes: number | null;
  resting_minutes: number | null;
};
export type RecipeYield = { amount: string; unit: string };
export type RecipePayload = {
  title: string;
  description: string | null;
  recipe_image_key?: string | null;
  group_ids: string[];
  tags: string[];
  time: RecipeTime;
  yield: RecipeYield;
  ingredient_sections: IngredientSection[];
  instructions: InstructionStep[];
  remarks: string | null;
};
export type Recipe = RecipePayload & {
  id: string;
  created_at: string;
  updated_at: string;
  version: number;
};
export type RecipeExportFormat = 'yaml' | 'markdown' | 'zip';
export type RecipeImportResponse = { imported: number; created: number; updated: number };
export type RecipeImportPreviewResponse = {
  imported: number;
  would_create: number;
  would_update: number;
};
export type RecipePurgeResponse = { ok: boolean; group_id: string | null; deleted_count: number };
export type ImageUploadResponse = {
  ok: boolean;
  bucket: string;
  key: string;
  size: number;
  content_type: string;
  view_url?: string;
  expires_in?: number;
};

export type SignedImageUrlResponse = {
  ok: boolean;
  key: string;
  view_url: string;
  expires_in: number;
};

export type Group = {
  id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
};
