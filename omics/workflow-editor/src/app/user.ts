export interface User {
  active: boolean;
  admin: boolean;
  admin_group_ids: [number];
  created_on: string;
  email: string;
  group_ids: [number];
  id: number;
  is_write_permitted: boolean;
  name: string;
  primary_user_group_id: number;
  updated_on: string;
  theme: string;
}
