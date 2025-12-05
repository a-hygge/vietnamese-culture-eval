"""
ChatGPT Web Interface Scraper
Tự động paste câu hỏi vào ChatGPT web và lấy câu trả lời.

Yêu cầu:
1. pip install selenium webdriver-manager
2. Đăng nhập ChatGPT trên Chrome trước khi chạy script
3. Giữ Chrome profile để không cần đăng nhập lại

Cách dùng:
    python chatgpt_web_scraper.py --input benchmark.json --output answers.json
    python chatgpt_web_scraper.py --limit 10  # Test với 10 câu
"""

import os
import json
import time
import argparse
from datetime import datetime

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    print("Cần cài đặt selenium và webdriver-manager:")
    print("  pip install selenium webdriver-manager")
    exit(1)


class ChatGPTWebScraper:
    """Scraper để lấy câu trả lời từ ChatGPT web interface."""

    def __init__(self, headless: bool = False, chrome_profile: str = None):
        """
        Khởi tạo scraper.

        Args:
            headless: Chạy không hiển thị browser (không khuyến khích vì cần đăng nhập)
            chrome_profile: Đường dẫn Chrome profile đã đăng nhập ChatGPT
        """
        self.driver = None
        self.headless = headless
        self.chrome_profile = chrome_profile

    def setup_driver(self, retry_count=0):
        """Cấu hình và khởi động Chrome driver."""
        import shutil
        import subprocess

        options = Options()

        if self.headless:
            options.add_argument("--headless")

        # Tạo profile riêng cho scraper (tránh conflict với Chrome đang mở)
        if self.chrome_profile:
            scraper_profile = self.chrome_profile
        else:
            scraper_profile = os.path.join(
                os.path.expanduser("~"),
                "AppData", "Local", "Google", "Chrome", "ChatGPT_Scraper_Profile"
            )

        # Nếu retry, xóa profile cũ
        if retry_count > 0 and os.path.exists(scraper_profile):
            print(f"  Xóa profile cũ và tạo mới...")
            try:
                shutil.rmtree(scraper_profile)
            except Exception as e:
                print(f"  ⚠ Không thể xóa profile: {e}")

        os.makedirs(scraper_profile, exist_ok=True)
        options.add_argument(f"--user-data-dir={scraper_profile}")
        print(f"  Sử dụng profile: {scraper_profile}")

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--start-maximized")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-gpu")
        options.add_argument("--remote-debugging-port=9222")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        # Tự động tải ChromeDriver
        print("  Đang khởi động Chrome...")

        try:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            print("✓ Chrome driver đã khởi động")

        except Exception as e:
            if retry_count < 2:
                print(f"  ⚠ Lỗi khởi động Chrome: {e}")
                print(f"  → Thử kill Chrome processes và retry...")

                # Kill Chrome processes
                try:
                    subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], capture_output=True)
                    subprocess.run(["taskkill", "/F", "/IM", "chromedriver.exe"], capture_output=True)
                except:
                    pass

                time.sleep(3)
                return self.setup_driver(retry_count + 1)
            else:
                raise e

    def open_chatgpt(self):
        """Mở trang ChatGPT và đợi load xong."""
        print("Đang mở ChatGPT...")
        self.driver.get("https://chatgpt.com/")
        time.sleep(3)

        # Kiểm tra đã đăng nhập chưa
        try:
            # Tìm textarea input (chỉ có khi đã đăng nhập)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "prompt-textarea"))
            )
            print("✓ Đã đăng nhập ChatGPT")
            return True
        except:
            print("⚠ Chưa đăng nhập ChatGPT!")
            print("  Vui lòng đăng nhập thủ công trong cửa sổ Chrome...")
            input("  Nhấn Enter sau khi đã đăng nhập...")
            return True

    def start_new_chat(self, retry_count=0):
        """Bắt đầu cuộc hội thoại mới với retry logic."""
        max_retries = 3

        try:
            # Cách 1: Click nút New Chat trong sidebar
            try:
                new_chat_btn = self.driver.find_element(By.CSS_SELECTOR, "a[data-testid='create-new-chat-button']")
                new_chat_btn.click()
                time.sleep(2)
                return True
            except:
                pass

            # Cách 2: Click logo/home
            try:
                new_chat_btn = self.driver.find_element(By.CSS_SELECTOR, "a[href='/']")
                new_chat_btn.click()
                time.sleep(2)
                return True
            except:
                pass

            # Cách 3: Dùng keyboard shortcut Ctrl+Shift+O (new chat)
            try:
                from selenium.webdriver.common.action_chains import ActionChains
                actions = ActionChains(self.driver)
                actions.key_down(Keys.CONTROL).key_down(Keys.SHIFT).send_keys('o').key_up(Keys.SHIFT).key_up(Keys.CONTROL).perform()
                time.sleep(2)
                return True
            except:
                pass

            # Cách 4: Refresh trang
            self.driver.get("https://chatgpt.com/")
            time.sleep(3)
            return True

        except Exception as e:
            print(f"  ⚠ Không thể tạo chat mới: {e}")

            if retry_count < max_retries:
                print(f"  → Retry {retry_count + 1}/{max_retries} sau 10 giây...")
                time.sleep(10)
                # Thử refresh trang
                try:
                    self.driver.get("https://chatgpt.com/")
                    time.sleep(5)
                    return self.start_new_chat(retry_count + 1)
                except:
                    pass

            # Fallback: refresh trang
            print(f"  → Fallback: refresh trang...")
            try:
                self.driver.get("https://chatgpt.com/")
                time.sleep(5)
            except:
                pass
            return False

    def send_message(self, message: str, retry_count=0) -> str:
        """
        Gửi tin nhắn và lấy câu trả lời.

        Args:
            message: Tin nhắn cần gửi
            retry_count: Số lần retry

        Returns:
            Câu trả lời từ ChatGPT
        """
        max_retries = 3

        try:
            # Đợi textarea sẵn sàng (presence + clickable)
            textarea = WebDriverWait(self.driver, 15).until(
                EC.element_to_be_clickable((By.ID, "prompt-textarea"))
            )

            # Đợi thêm để element ổn định
            time.sleep(1)

            # Scroll đến element
            self.driver.execute_script("arguments[0].scrollIntoView(true);", textarea)
            time.sleep(0.5)

            # Click vào textarea trước khi nhập
            try:
                textarea.click()
                time.sleep(0.3)
            except:
                # Dùng JavaScript click nếu click thường không được
                self.driver.execute_script("arguments[0].click();", textarea)
                time.sleep(0.3)

            # ChatGPT dùng contenteditable div (ProseMirror), không phải textarea thường
            # Ưu tiên dùng clipboard để paste toàn bộ message (bao gồm newlines)

            input_success = False

            # Cách 1 (ƯU TIÊN): Dùng clipboard - paste toàn bộ message cùng lúc
            try:
                import pyperclip
                pyperclip.copy(message)
                textarea.click()
                time.sleep(0.3)
                # Ctrl+V để paste
                from selenium.webdriver.common.action_chains import ActionChains
                actions = ActionChains(self.driver)
                actions.key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
                time.sleep(0.5)
                print(f"    [Đã paste {len(message)} ký tự từ clipboard]")
                input_success = True
            except Exception as e1:
                print(f"    clipboard failed: {e1}, thử send_keys...")

            # Cách 2: send_keys - nhưng phải xử lý newlines cẩn thận
            if not input_success:
                try:
                    textarea.clear()
                    time.sleep(0.2)
                    # Thay \n bằng Shift+Enter để không gửi message sớm
                    from selenium.webdriver.common.action_chains import ActionChains
                    actions = ActionChains(self.driver)
                    actions.click(textarea)

                    # Chia message theo newlines và xử lý từng phần
                    parts = message.split('\n')
                    for i, part in enumerate(parts):
                        if part:  # Chỉ gõ nếu có nội dung
                            actions.send_keys(part)
                        if i < len(parts) - 1:  # Không thêm newline sau phần cuối
                            # Shift+Enter để xuống dòng mà không gửi
                            actions.key_down(Keys.SHIFT).send_keys(Keys.ENTER).key_up(Keys.SHIFT)

                    actions.perform()
                    time.sleep(0.5)
                    print(f"    [Đã nhập {len(message)} ký tự bằng send_keys với Shift+Enter]")
                    input_success = True
                except Exception as e2:
                    print(f"    send_keys failed: {e2}, thử JS...")

            # Cách 3: JavaScript - fallback cuối cùng
            if not input_success:
                try:
                    # Dùng insertText command
                    self.driver.execute_script("""
                        var el = arguments[0];
                        var text = arguments[1];
                        el.focus();
                        el.click();
                        // Clear existing content
                        el.innerHTML = '';
                        // Insert text using execCommand (deprecated but still works)
                        document.execCommand('insertText', false, text);
                    """, textarea, message)
                    time.sleep(0.5)
                    print(f"    [Đã nhập {len(message)} ký tự bằng JS insertText]")
                except Exception as e3:
                    print(f"    JS insertText failed: {e3}")

            time.sleep(0.5)

            # Kiểm tra xem text đã được nhập vào chưa
            try:
                current_text = textarea.text or textarea.get_attribute("textContent") or ""
                if not current_text.strip():
                    # Text chưa được nhập, thử lại với ActionChains
                    print("    ⚠ Text chưa được nhập, thử ActionChains...")
                    from selenium.webdriver.common.action_chains import ActionChains
                    textarea.click()
                    time.sleep(0.3)
                    actions = ActionChains(self.driver)
                    actions.send_keys(message).perform()
                    time.sleep(0.5)
            except:
                pass

            # Gửi tin nhắn (click button hoặc Enter)
            try:
                send_btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='send-button']"))
                )
                send_btn.click()
            except:
                # Fallback: dùng Enter
                textarea.send_keys(Keys.ENTER)

            # Đợi response
            print("    Đang chờ ChatGPT trả lời...", end="", flush=True)

            # Đợi cho đến khi có response mới
            time.sleep(3)

            # Đợi cho đến khi ChatGPT ngừng gõ
            max_wait = 90  # Tối đa 90 giây
            start_time = time.time()
            last_text = ""
            stable_count = 0
            no_response_count = 0  # Đếm số lần không có response

            while time.time() - start_time < max_wait:
                try:
                    # === KIỂM TRA RATE LIMIT ===
                    # Tìm các thông báo lỗi rate limit
                    rate_limit_detected = False

                    # Kiểm tra các selector phổ biến cho rate limit message
                    rate_limit_selectors = [
                        "div[class*='rate-limit']",
                        "div[class*='error']",
                        "div:contains('limit')",
                        "div:contains('too many')",
                        "div:contains('slow down')",
                        "div:contains('try again')",
                    ]

                    # Kiểm tra text trên page
                    page_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
                    rate_limit_keywords = [
                        "you've reached",
                        "rate limit",
                        "too many requests",
                        "please slow down",
                        "try again later",
                        "usage cap",
                        "limit reached",
                        "come back",
                        "temporarily unavailable"
                    ]

                    for keyword in rate_limit_keywords:
                        if keyword in page_text:
                            rate_limit_detected = True
                            print(f"\n    ⚠ RATE LIMIT DETECTED: '{keyword}'")
                            break

                    if rate_limit_detected:
                        return "[RATE_LIMIT]"

                    # Kiểm tra nút stop (đang generate)
                    stop_btns = self.driver.find_elements(By.CSS_SELECTOR, "button[aria-label='Stop generating']")

                    # Lấy text hiện tại
                    responses = self.driver.find_elements(By.CSS_SELECTOR, "div[data-message-author-role='assistant']")
                    current_text = ""
                    if responses:
                        try:
                            content = responses[-1].find_element(By.CSS_SELECTOR, "div.markdown")
                            current_text = content.text.strip()
                        except:
                            current_text = responses[-1].text.strip()

                    # Kiểm tra đã stable chưa (text không đổi trong 3 giây)
                    if current_text and current_text == last_text:
                        stable_count += 1
                        if stable_count >= 3 and not stop_btns:
                            # Text stable 3 giây và không còn nút stop = xong
                            break
                    else:
                        stable_count = 0
                        last_text = current_text

                    # Nếu không có response sau 15 giây và không có nút stop
                    if not current_text and not stop_btns:
                        no_response_count += 1
                        if no_response_count >= 15:  # 15 giây không có gì
                            print("\n    ⚠ Không có response sau 15 giây - có thể bị rate limit")
                            return "[NO_RESPONSE_TIMEOUT]"

                    if not stop_btns and stable_count >= 2:
                        break

                except:
                    pass
                time.sleep(1)
                print(".", end="", flush=True)

            print(" Done!")
            time.sleep(1)

            # Lấy response cuối cùng
            responses = self.driver.find_elements(By.CSS_SELECTOR, "div[data-message-author-role='assistant']")

            if responses:
                last_response = responses[-1]
                # Lấy text từ markdown content
                try:
                    content = last_response.find_element(By.CSS_SELECTOR, "div.markdown")
                    return content.text.strip()
                except:
                    return last_response.text.strip()
            else:
                return "[NO RESPONSE]"

        except Exception as e:
            error_msg = str(e)
            print(f" Error: {error_msg}")

            # Retry nếu là lỗi element not interactable
            if retry_count < max_retries and ("not interactable" in error_msg or "stale element" in error_msg.lower()):
                print(f"    → Retry {retry_count + 1}/{max_retries}...")
                time.sleep(3)

                # Refresh trang và thử lại
                try:
                    self.driver.get("https://chatgpt.com/")
                    time.sleep(3)
                    return self.send_message(message, retry_count + 1)
                except:
                    pass

            return f"[ERROR: {error_msg}]"

    def get_answer(self, context: str, question: str) -> str:
        """
        Lấy câu trả lời cho một câu hỏi.

        Args:
            context: Context của câu hỏi
            question: Câu hỏi

        Returns:
            Câu trả lời từ ChatGPT
        """
        # Format message với instruction yêu cầu trả lời ngắn gọn
        # Giống như khi người dùng paste vào web
        instruction = "Trả lời ngắn gọn, đi thẳng vào vấn đề (1-3 câu). Không cần giải thích dài dòng."

        if context:
            message = f"{context}\n\n{question}\n\n({instruction})"
        else:
            message = f"{question}\n\n({instruction})"

        return self.send_message(message)

    def close(self):
        """Đóng browser."""
        if self.driver:
            self.driver.quit()
            print("✓ Đã đóng browser")


def load_benchmark(json_path: str) -> list:
    """Load benchmark data từ JSON file."""
    if not os.path.exists(json_path):
        return []

    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_progress(progress_file: str) -> dict:
    """Load progress từ file."""
    if os.path.exists(progress_file):
        with open(progress_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_progress(progress_file: str, answers: dict):
    """Lưu progress vào file."""
    with open(progress_file, 'w', encoding='utf-8') as f:
        json.dump(answers, f, ensure_ascii=False, indent=2)


def main():
    parser = argparse.ArgumentParser(description='Lấy câu trả lời từ ChatGPT Web')

    parser.add_argument('--input', type=str, default=None,
                        help='Path to benchmark JSON file')
    parser.add_argument('--output', type=str, default=None,
                        help='Path to output answers JSON file')
    parser.add_argument('--limit', type=int, default=None,
                        help='Giới hạn số câu hỏi')
    parser.add_argument('--start-from', type=int, default=0,
                        help='Bắt đầu từ câu hỏi thứ mấy')

    args = parser.parse_args()

    # Default paths
    base_dir = r"D:/dichdata/vietnamese-culture-eval-2"

    if not args.input:
        # Load từ chunk files
        args.input = os.path.join(base_dir, "data_question_answer", "ban_sac_van_hoa_viet_nam", "culture_benchmark.json")

    if not args.output:
        args.output = os.path.join(base_dir, "chatgpt_web_answers.json")

    progress_file = args.output  # Dùng luôn output file làm progress

    print("=" * 60)
    print("CHATGPT WEB SCRAPER")
    print("=" * 60)
    print(f"Input:  {args.input}")
    print(f"Output: {args.output}")

    # Load data
    print("\nLoading benchmark data...")
    data = load_benchmark(args.input)

    if not data:
        print(f"⚠ Không tìm thấy data trong {args.input}")
        return

    # Load existing answers
    answers = load_progress(progress_file)
    print(f"  Đã có {len(answers)} câu trả lời từ trước")

    # Apply limit
    if args.limit:
        data = data[:args.limit]

    print(f"  Tổng số câu hỏi: {len(data)}")

    # Khởi động scraper
    print("\n" + "=" * 60)
    print("KHỞI ĐỘNG CHROME")
    print("=" * 60)
    print("\n⚠ LƯU Ý:")
    print("  1. Script sẽ mở Chrome với profile riêng (không ảnh hưởng Chrome đang mở)")
    print("  2. Lần đầu chạy: cần đăng nhập ChatGPT thủ công")
    print("  3. Các lần sau: đã lưu session, không cần đăng nhập lại")
    print("  4. Progress được lưu sau mỗi câu - có thể dừng và tiếp tục")
    print()

    input("Nhấn Enter để bắt đầu...")

    scraper = ChatGPTWebScraper()

    try:
        scraper.setup_driver()
        scraper.open_chatgpt()

        print("\n" + "=" * 60)
        print("BẮT ĐẦU LẤY CÂU TRẢ LỜI")
        print("=" * 60)

        consecutive_errors = 0
        max_consecutive_errors = 5

        for idx, item in enumerate(data):
            if idx < args.start_from:
                continue

            item_id = item.get("id", f"Q{idx}")

            # Skip nếu đã có answer
            if item_id in answers:
                print(f"[{idx+1}/{len(data)}] {item_id} - Đã có, bỏ qua")
                continue

            print(f"\n[{idx+1}/{len(data)}] {item_id}")

            # LUÔN tạo chat mới cho mỗi câu hỏi để tránh context pollution
            print("  → Tạo chat mới...")
            if not scraper.start_new_chat():
                print("  ⚠ Không thể tạo chat mới, đợi 30 giây rồi thử lại...")
                time.sleep(30)
                if not scraper.start_new_chat():
                    print("  ✗ Vẫn không thể tạo chat mới, bỏ qua câu này")
                    consecutive_errors += 1
                    if consecutive_errors >= max_consecutive_errors:
                        print(f"\n⚠ Quá nhiều lỗi liên tiếp ({max_consecutive_errors}), dừng script")
                        break
                    continue

            time.sleep(2)  # Tăng delay sau khi tạo chat mới

            context = item.get("context", "")
            question = item.get("question", "")

            print(f"  Q: {question[:60]}...")

            # Lấy answer
            answer = scraper.get_answer(context, question)

            # Kiểm tra answer có hợp lệ không
            if answer.startswith("[ERROR") or answer == "[NO RESPONSE]":
                print(f"  ⚠ Lỗi: {answer}")
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    print(f"\n⚠ Quá nhiều lỗi liên tiếp ({max_consecutive_errors}), dừng script")
                    break
                time.sleep(10)
                continue

            # === XỬ LÝ RATE LIMIT ===
            if answer in ["[RATE_LIMIT]", "[NO_RESPONSE_TIMEOUT]"]:
                print(f"\n{'='*60}")
                print("⚠ RATE LIMIT DETECTED - TẠM DỪNG")
                print("="*60)
                print(f"  Câu hỏi hiện tại: {item_id}")
                print(f"  Đã hoàn thành: {len(answers)} câu")
                print()

                # Hỏi user muốn đợi hay dừng
                print("  Bạn có thể:")
                print("  1. Đợi 1-2 tiếng rồi tiếp tục (ChatGPT free limit)")
                print("  2. Dừng script và chạy lại sau")
                print()

                wait_minutes = 60  # Mặc định đợi 60 phút
                try:
                    user_input = input(f"  Nhập số phút muốn đợi (Enter = {wait_minutes} phút, 0 = dừng): ").strip()
                    if user_input == "0":
                        print("  → Dừng script theo yêu cầu")
                        break
                    elif user_input:
                        wait_minutes = int(user_input)
                except:
                    pass

                print(f"\n  ⏳ Đợi {wait_minutes} phút trước khi tiếp tục...")
                print(f"  (Có thể nhấn Ctrl+C để dừng)")

                # Đợi với countdown
                for remaining in range(wait_minutes * 60, 0, -30):
                    mins = remaining // 60
                    secs = remaining % 60
                    print(f"\r  ⏳ Còn {mins:02d}:{secs:02d}...", end="", flush=True)
                    time.sleep(30)

                print("\n  → Tiếp tục...")

                # Refresh trang và thử lại
                try:
                    scraper.driver.get("https://chatgpt.com/")
                    time.sleep(5)
                except:
                    pass

                # Không tăng consecutive_errors vì đã đợi
                continue

            # Reset error counter khi thành công
            consecutive_errors = 0

            print(f"  A: {answer[:60]}...")

            # Lưu
            answers[item_id] = {
                "question": question,
                "context": context,
                "gpt_web_answer": answer,
                "timestamp": datetime.now().isoformat()
            }

            # Save progress sau mỗi câu
            save_progress(progress_file, answers)
            print(f"  ✓ Saved ({len(answers)} total)")

            # Delay để tránh rate limit
            time.sleep(2)

    except KeyboardInterrupt:
        print("\n\n⚠ Đã dừng bởi người dùng")
    except Exception as e:
        print(f"\n✗ Lỗi: {str(e)}")
    finally:
        scraper.close()

    print("\n" + "=" * 60)
    print("HOÀN THÀNH")
    print("=" * 60)
    print(f"Đã lấy được {len(answers)} câu trả lời")
    print(f"Lưu tại: {args.output}")


if __name__ == "__main__":
    main()
