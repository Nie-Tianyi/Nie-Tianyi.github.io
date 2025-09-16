import glob
import os
import re
import requests
import argparse
from urllib.parse import urlparse, urljoin
import hashlib

class MarkdownImageDownloader:
    def __init__(self, markdown_file, output_dir="images", base_url=None):
        self.markdown_file = markdown_file
        self.output_dir = output_dir
        self.base_url = base_url
        self.downloaded_images = {}

        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

    def extract_image_urls(self):
        """从Markdown文件中提取所有图片URL"""
        image_urls = []

        with open(self.markdown_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 提取Markdown格式的图片 ![](url)
        markdown_pattern = r'!\[.*?\]\((.*?)\)'
        markdown_images = re.findall(markdown_pattern, content)
        image_urls.extend(markdown_images)

        # 提取HTML格式的图片 <img src="url">
        html_pattern = r'<img[^>]+src="([^">]+)"'
        html_images = re.findall(html_pattern, content)
        image_urls.extend(html_images)

        # 提取自闭合的HTML img标签
        self_closing_pattern = r'<img[^>]+src="([^">]+)"[^>]*/>'
        self_closing_images = re.findall(self_closing_pattern, content)
        image_urls.extend(self_closing_images)

        return image_urls

    def download_image(self, url, filename):
        """下载单个图片到指定文件名"""
        try:
            # 处理相对URL
            if self.base_url and not url.startswith(('http://', 'https://')):
                url = urljoin(self.base_url, url)

            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            # 确定文件扩展名
            content_type = response.headers.get('content-type', '')
            if 'svg' in content_type or url.endswith('.svg'):
                if not filename.endswith('.svg'):
                    filename += '.svg'

            with open(filename, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            print(f"下载成功: {url} -> {filename}")
            return True
        except Exception as e:
            print(f"下载失败 {url}: {e}")
            return False

    def generate_local_filename(self, url, index):
        """根据URL生成本地文件名"""
        # 从URL中提取文件名
        parsed_url = urlparse(url)
        path = parsed_url.path

        if path:
            filename = os.path.basename(path)
            # 如果没有扩展名，尝试从Content-Type推断
            if '.' not in filename:
                # 使用URL的MD5哈希作为文件名
                url_hash = hashlib.md5(url.encode()).hexdigest()
                filename = f"image_{url_hash[:8]}.png"
        else:
            # 如果没有路径，使用索引作为文件名
            filename = f"image_{index}.png"

        return os.path.join(self.output_dir, filename)

    def download_all_images(self):
        """下载所有图片"""
        image_urls = self.extract_image_urls()
        print(f"找到 {len(image_urls)} 个图片引用")

        for i, url in enumerate(image_urls):
            if not url.strip():  # 跳过空URL
                continue

            local_path = self.generate_local_filename(url, i)

            # 避免重复下载相同URL
            if url in self.downloaded_images:
                continue

            if self.download_image(url, local_path):
                self.downloaded_images[url] = local_path

    def update_markdown_with_local_paths(self, output_file=None):
        """更新Markdown文件，将图片引用替换为本地路径"""
        if not output_file:
            base_name = os.path.splitext(self.markdown_file)[0]
            output_file = f"{base_name}_preprocessed.md"

        with open(self.markdown_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 替换Markdown格式的图片引用
        def markdown_replacer(match):
            alt_text = match.group(1) if match.group(1) else ""
            url = match.group(2)
            if url in self.downloaded_images:
                return f"![{alt_text}]({self.downloaded_images[url]})"
            return match.group(0)

        markdown_pattern = r'!\[(.*?)\]\((.*?)\)'
        content = re.sub(markdown_pattern, markdown_replacer, content)

        # 替换HTML格式的图片引用
        def html_replacer(match):
            full_match = match.group(0)
            url = match.group(1)
            if url in self.downloaded_images:
                return full_match.replace(url, self.downloaded_images[url])
            return full_match

        html_pattern = r'<img[^>]+src="([^">]+)"[^>]*>'
        content = re.sub(html_pattern, html_replacer, content)

        # 写入更新后的内容
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"已更新Markdown文件: {output_file}")
        return output_file

def find_markdown_files():
    """查找当前目录及其子目录中的所有Markdown文件"""
    markdown_files = []

    # 使用glob递归查找所有.md文件
    for file_path in glob.glob('source_markdowns/*.md', recursive=True):
        if os.path.isfile(file_path):  # 确保是文件而不是目录
            markdown_files.append(os.path.abspath(file_path))

    return markdown_files



def main():
    markdown_files = find_markdown_files()
    for path in markdown_files:
        print(f"Processing: {path}")
        f_name = os.path.basename(path)
        f_name = f_name.replace(" ", "_")
        downloader = MarkdownImageDownloader(
            markdown_file=f"source_markdowns/{f_name}",
            output_dir=f"images/{f_name.split('.')[0]}",
        )
        downloader.download_all_images()
        downloader.update_markdown_with_local_paths(f"output/{f_name.split('.')[0]}_preprocessed.md")

if __name__ == "__main__":
    main()