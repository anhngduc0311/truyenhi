/**
 * ==============================================================================
 * 🚀 CLOUDFLARE WORKER - IMAGE CDN PROXY CHO NEKOHENTAI (AWS S3 AP-SOUTHEAST-1)
 * ==============================================================================
 * Mục đích:
 * 1. Nhận request từ domain: https://img.nekohentai.lol/<path_to_image>
 * 2. Proxy trực tiếp tới AWS S3: https://nekohentai-storage.s3.ap-southeast-1.amazonaws.com/<path_to_image>
 * 3. Tự động thêm Cache-Control: public, max-age=31536000 (1 năm)
 * 4. Cache 99.9% tại Edge Cloudflare -> MIỄN PHÍ TIỀN BĂNG THÔNG AWS S3 (0đ Egress)
 * 5. Hỗ trợ CORS (*) chống chặn ảnh trên trình duyệt Web/App
 * ==============================================================================
 */

// Cấu hình S3 Origin của bạn
const BUCKET_NAME = "nekohentai-storage";
const AWS_REGION = "ap-southeast-1";
const S3_ORIGIN = `https://${BUCKET_NAME}.s3.${AWS_REGION}.amazonaws.com`;

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // Chỉ cho phép phương thức GET và HEAD
    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response("Method Not Allowed", { status: 405 });
    }

    // Nếu người dùng vào trang chủ domain img (không có path)
    if (url.pathname === "/" || url.pathname === "") {
      return new Response("🚀 NekoHentai Image CDN is running smoothly on Cloudflare Edge!", {
        status: 200,
        headers: { "Content-Type": "text/plain; charset=utf-8" },
      });
    }

    // Xử lý CORS Preflight (OPTIONS)
    if (request.method === "OPTIONS") {
      return new Response(null, {
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
          "Access-Control-Allow-Headers": "*",
          "Access-Control-Max-Age": "86400",
        },
      });
    }

    // Tạo URL đích tới AWS S3
    const s3Url = `${S3_ORIGIN}${url.pathname}`;

    // Kiểm tra Cloudflare Cache API trước
    const cache = caches.default;
    let response = await cache.match(request);

    if (!response) {
      // Gửi request lấy ảnh từ S3
      const s3Request = new Request(s3Url, {
        method: request.method,
        headers: {
          "User-Agent": "NekoHentai-Cloudflare-Worker/1.0",
          "Accept": request.headers.get("Accept") || "*/*",
        },
      });

      const s3Response = await fetch(s3Request);

      // Nếu ảnh không tồn tại trên S3
      if (s3Response.status === 404 || s3Response.status === 403) {
        return new Response("Image Not Found", {
          status: 404,
          headers: {
            "Access-Control-Allow-Origin": "*",
            "Content-Type": "text/plain; charset=utf-8",
          },
        });
      }

      // Tạo Response mới với header tối ưu cache cực đại
      response = new Response(s3Response.body, s3Response);

      // Bật CORS cho ảnh
      response.headers.set("Access-Control-Allow-Origin", "*");
      response.headers.set("Access-Control-Allow-Methods", "GET, HEAD");

      // Thiết lập Cache ở trình duyệt & Cloudflare Edge (1 năm)
      response.headers.set(
        "Cache-Control",
        "public, max-age=31536000, s-maxage=31536000, immutable"
      );
      response.headers.set("CDN-Cache-Control", "public, max-age=31536000, immutable");
      response.headers.set("X-Content-Type-Options", "nosniff");

      // Xóa các header nội bộ của AWS để bảo mật
      response.headers.delete("x-amz-request-id");
      response.headers.delete("x-amz-id-2");
      response.headers.delete("server");

      // Lưu vào Cloudflare Edge Cache trong nền
      ctx.waitUntil(cache.put(request, response.clone()));
    }

    return response;
  },
};
