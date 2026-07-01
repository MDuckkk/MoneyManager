import {
  ConflictException,
  Injectable,
  UnauthorizedException,
} from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { JwtService } from '@nestjs/jwt';
import { ConfigService } from '@nestjs/config';
import * as bcrypt from 'bcrypt';
import { User } from '../users/entities/user.entity';
import { Category } from '../categories/entities/category.entity';
import { DEFAULT_CATEGORIES } from '../categories/constants/default-categories';
import { RegisterDto } from './dto/register.dto';
import { LoginDto } from './dto/login.dto';

@Injectable()
export class AuthService {
  constructor(
    @InjectRepository(User)
    private readonly usersRepository: Repository<User>,
    @InjectRepository(Category)
    private readonly categoriesRepository: Repository<Category>,
    private readonly jwtService: JwtService,
    private readonly configService: ConfigService,
  ) {}

  async register(dto: RegisterDto) {
    const email = dto.email.trim().toLowerCase();

    const existing = await this.usersRepository.findOne({ where: { email } });
    if (existing) {
      throw new ConflictException('Email đã được sử dụng');
    }

    const saltRounds = this.configService.get<number>('jwt.saltRounds') ?? 10;
    const passwordHash = await bcrypt.hash(dto.password, saltRounds);

    const user = await this.usersRepository.save(
      this.usersRepository.create({
        email,
        passwordHash,
        name: dto.name?.trim() || null,
      }),
    );

    await this.createDefaultCategories(user.id);

    return {
      success: true,
      message: 'Đăng ký thành công',
      data: await this.buildAuthPayload(user),
    };
  }

  async login(dto: LoginDto) {
    const email = dto.email.trim().toLowerCase();
    const user = await this.usersRepository.findOne({ where: { email } });

    if (!user || !(await bcrypt.compare(dto.password, user.passwordHash))) {
      throw new UnauthorizedException({
        message: 'Email hoặc mật khẩu không chính xác',
        code: 'INVALID_CREDENTIALS',
      });
    }

    return {
      success: true,
      message: 'Đăng nhập thành công',
      data: await this.buildAuthPayload(user),
    };
  }

  async refreshToken(refreshToken: string | undefined) {
    if (!refreshToken) {
      throw new UnauthorizedException({
        message: 'Yêu cầu refresh token',
        code: 'REFRESH_TOKEN_REQUIRED',
      });
    }

    let payload: { sub: number; userId: number };
    try {
      payload = await this.jwtService.verifyAsync(refreshToken, {
        secret: this.configService.get<string>('jwt.refreshTokenSecret'),
      });
    } catch {
      throw new UnauthorizedException({
        message: 'Refresh token không hợp lệ hoặc đã hết hạn',
        code: 'REFRESH_TOKEN_INVALID',
      });
    }

    const user = await this.usersRepository.findOne({
      where: { id: payload.userId },
    });
    if (!user) {
      throw new UnauthorizedException('Không tìm thấy người dùng');
    }

    return {
      success: true,
      message: 'Làm mới token thành công',
      data: { accessToken: await this.createAccessToken(user) },
    };
  }

  async me(userId: number) {
    const user = await this.usersRepository.findOne({ where: { id: userId } });
    if (!user) throw new UnauthorizedException('Không tìm thấy người dùng');
    return { success: true, message: 'Success', data: this.toSafeUser(user) };
  }

  logout() {
    // Token là stateless (JWT); client tự xóa token. Endpoint giữ để nhất quán.
    return { success: true, message: 'Đăng xuất thành công', data: null };
  }

  private async buildAuthPayload(user: User) {
    return {
      user: this.toSafeUser(user),
      accessToken: await this.createAccessToken(user),
      refreshToken: await this.createRefreshToken(user),
    };
  }

  private createAccessToken(user: User) {
    return this.jwtService.signAsync(
      { sub: user.id, userId: user.id },
      {
        secret: this.configService.get<string>('jwt.secret'),
        expiresIn:
          this.configService.get<string>('jwt.accessTokenExpiresIn') ?? '15m',
      } as any,
    );
  }

  private createRefreshToken(user: User) {
    return this.jwtService.signAsync(
      { sub: user.id, userId: user.id },
      {
        secret: this.configService.get<string>('jwt.refreshTokenSecret'),
        expiresIn:
          this.configService.get<string>('jwt.refreshTokenExpiresIn') ?? '7d',
      } as any,
    );
  }

  private async createDefaultCategories(userId: number) {
    const categories = DEFAULT_CATEGORIES.map((c) =>
      this.categoriesRepository.create({ ...c, userId }),
    );
    await this.categoriesRepository.save(categories);
  }

  private toSafeUser(user: User) {
    return {
      id: user.id,
      email: user.email,
      name: user.name,
      createdAt: user.createdAt,
    };
  }
}
