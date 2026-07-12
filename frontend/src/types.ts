export type Role = 'admin' | 'author' | 'reader';

export type GroupRole = {
  group_id: string;
  role: Role;
};

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

export type TokenResponse = {
  access_token: string;
  token_type: string;
  user: UserPublic;
};

export type HealthResponse = {
  status: string;
  service: string;
  time: string;
};

export type SystemCheckItem = {
  ok: boolean;
  endpoint?: string;
  bucket?: string;
  error?: string;
};

export type SystemChecksResponse = {
  api: SystemCheckItem;
  mongodb: SystemCheckItem;
  s3: SystemCheckItem;
  ok: boolean;
};

export type Recipe = {
  id: string;
  title: string;
  description: string | null;
  tags: string[];
  created_at: string;
};

export type ImageUploadResponse = {
  ok: boolean;
  bucket: string;
  key: string;
  size: number;
  content_type: string;
};
