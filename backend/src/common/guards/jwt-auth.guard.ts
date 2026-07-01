import {
  CanActivate,
  ExecutionContext,
  Injectable,
  UnauthorizedException,
} from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { JwtService } from '@nestjs/jwt';
import { Request } from 'express';
import { IS_PUBLIC_KEY } from '../decorators/public.decorator';

type AuthJwtPayload = {
  sub: number;
  userId: number;
};

@Injectable()
export class JwtAuthGuard implements CanActivate {
  constructor(
    private readonly reflector: Reflector,
    private readonly jwtService: JwtService,
  ) {}

  async canActivate(context: ExecutionContext): Promise<boolean> {
    const isPublic = this.reflector.getAllAndOverride<boolean>(IS_PUBLIC_KEY, [
      context.getHandler(),
      context.getClass(),
    ]);

    if (isPublic) {
      return true;
    }

    const request = context
      .switchToHttp()
      .getRequest<Request & { user?: AuthJwtPayload }>();
    const token = this.extractTokenFromHeader(request);

    if (!token) {
      throw new UnauthorizedException({
        message: 'Yêu cầu access token',
        code: 'ACCESS_TOKEN_REQUIRED',
      });
    }

    try {
      request.user = await this.jwtService.verifyAsync<AuthJwtPayload>(token);
      return true;
    } catch (error) {
      throw new UnauthorizedException({
        message: 'Access token không hợp lệ hoặc đã hết hạn',
        code:
          error instanceof Error && error.name === 'TokenExpiredError'
            ? 'TOKEN_EXPIRED'
            : 'TOKEN_INVALID',
      });
    }
  }

  private extractTokenFromHeader(request: Request): string | undefined {
    const [type, token] = request.headers.authorization?.split(' ') ?? [];
    return type === 'Bearer' ? token : undefined;
  }
}
