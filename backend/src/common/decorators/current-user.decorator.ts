import { createParamDecorator, ExecutionContext } from '@nestjs/common';

/**
 * Lấy user đã xác thực (do JwtAuthGuard gắn vào request).
 * Dùng: handler(@CurrentUser() user: AuthUser) hoặc @CurrentUser('userId') id: number
 */
export const CurrentUser = createParamDecorator(
  (data: string, ctx: ExecutionContext) => {
    const request = ctx.switchToHttp().getRequest();
    const user = request.user;
    return data ? user?.[data] : user;
  },
);
