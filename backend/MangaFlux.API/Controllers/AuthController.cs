using System;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Http;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.RateLimiting;
using NekoHentai.API.DTOs;
using NekoHentai.API.Services;

namespace NekoHentai.API.Controllers
{
    [ApiController]
    [Route("api/[controller]")]
    public class AuthController : ControllerBase
    {
        private readonly IAuthService _authService;

        public AuthController(IAuthService authService)
        {
            _authService = authService;
        }

        [HttpPost("register")]
        [EnableRateLimiting("auth-limiter")]
        public async Task<IActionResult> Register([FromBody] RegisterDto dto)
        {
            var result = await _authService.RegisterAsync(dto);
            if (result == null)
            {
                return BadRequest(new { message = "Tên đăng nhập hoặc email đã tồn tại." });
            }

            SetRefreshTokenCookie(result.RefreshToken);
            return Ok(result.Response);
        }

        [HttpPost("login")]
        [EnableRateLimiting("auth-limiter")]
        public async Task<IActionResult> Login([FromBody] LoginDto dto)
        {
            var result = await _authService.LoginAsync(dto);
            if (result == null)
            {
                return Unauthorized(new { message = "Tài khoản hoặc mật khẩu không chính xác." });
            }

            SetRefreshTokenCookie(result.RefreshToken);
            return Ok(result.Response);
        }

        [HttpPost("google-login")]
        public async Task<IActionResult> GoogleLogin([FromBody] GoogleLoginDto dto)
        {
            if (string.IsNullOrWhiteSpace(dto.IdToken))
            {
                return BadRequest(new { message = "Google ID Token không hợp lệ." });
            }

            var result = await _authService.GoogleLoginAsync(dto.IdToken);
            if (result == null)
            {
                return Unauthorized(new { message = "Xác thực tài khoản Google thất bại hoặc tài khoản đã bị khóa." });
            }

            SetRefreshTokenCookie(result.RefreshToken);
            return Ok(result.Response);
        }

        [HttpPost("refresh-token")]
        public async Task<IActionResult> RefreshToken()
        {
            var refreshToken = Request.Cookies["nekohentai_refresh_token"];
            if (string.IsNullOrEmpty(refreshToken))
            {
                return Unauthorized(new { message = "Không tìm thấy Refresh Token." });
            }

            var result = await _authService.RefreshTokenAsync(refreshToken);
            if (result == null)
            {
                ClearRefreshTokenCookie();
                return Unauthorized(new { message = "Refresh Token không hợp lệ hoặc đã hết hạn." });
            }

            SetRefreshTokenCookie(result.RefreshToken);
            return Ok(result.Response);
        }

        [HttpPost("logout")]
        public async Task<IActionResult> Logout()
        {
            var refreshToken = Request.Cookies["nekohentai_refresh_token"];
            if (!string.IsNullOrEmpty(refreshToken))
            {
                await _authService.RevokeRefreshTokenAsync(refreshToken);
            }

            ClearRefreshTokenCookie();
            return Ok(new { message = "Đăng xuất thành công." });
        }

        private void SetRefreshTokenCookie(string refreshToken)
        {
            var cookieOptions = new CookieOptions
            {
                HttpOnly = true,
                Expires = DateTime.UtcNow.AddDays(7),
                SameSite = SameSiteMode.Lax,
                Secure = Request.IsHttps,
                Path = "/api/auth"
            };
            Response.Cookies.Append("nekohentai_refresh_token", refreshToken, cookieOptions);
        }

        private void ClearRefreshTokenCookie()
        {
            Response.Cookies.Delete("nekohentai_refresh_token", new CookieOptions
            {
                HttpOnly = true,
                SameSite = SameSiteMode.Lax,
                Secure = Request.IsHttps,
                Path = "/api/auth"
            });
        }
    }
}

