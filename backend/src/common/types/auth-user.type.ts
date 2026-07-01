/**
 * Payload người dùng được giải mã từ access token, gắn vào request.user.
 * App quản lý chi tiêu chỉ có 1 vai trò người dùng nên không cần role.
 */
export type AuthUser = {
  userId: number;
  sub: number;
};
