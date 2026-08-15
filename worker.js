/**
 * Worker phục vụ site tĩnh trên Cloudflare.
 *
 * Vì sao cần file này thay vì để Cloudflare tự lo:
 *
 * 1. Mặc định Cloudflare cắt đuôi .html — /abc.html bị 307 sang /abc. Website
 *    đã chạy nhiều năm với 227 URL dạng .html đã được Google index, đổi là mất
 *    thứ hạng. Tắt bằng "html_handling": "none" trong wrangler.jsonc.
 *
 * 2. Tắt xong thì "/" không còn tự trỏ vào index.html nữa — trang chủ 404.
 *
 * 3. Vá bằng cách rewrite "/" sang "/index.html" thì hỏng kiểu khác: Cloudflare
 *    có luật riêng LUÔN 301 /index.html về /, không tắt được bằng html_handling.
 *    Worker nhận lại cái 301 và trả về nguyên xi → / redirect về / → vòng lặp.
 *
 * Nên "/" được phục vụ từ home.html — bản sao y hệt index.html do build.py sinh
 * ra, mang tên khác để không dính luật trên. Đây là rewrite nội bộ, KHÔNG
 * redirect: thanh địa chỉ vẫn là "/", không sinh thêm URL nào cho Google.
 */
export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === '/') {
      const home = new URL(url);
      home.pathname = '/home.html';
      const res = await env.ASSETS.fetch(new Request(home, request));
      if (res.ok) return res;
    }

    return env.ASSETS.fetch(request);
  }
};
