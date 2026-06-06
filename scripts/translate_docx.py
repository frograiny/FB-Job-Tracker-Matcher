import docx

def main():
    doc = docx.Document('/home/truongan/Downloads/resume_truongan.docx')
    
    translations = {
        "DINH TRUONG AN": "ĐINH TRƯỜNG AN",
        "EDUCATION": "HỌC VẤN",
        "B.Sc. Computer and Information Science  |  University of Science - VNU": "B.Sc. Khoa học Máy tính và Thông tin  |  Trường Đại học Khoa học Tự nhiên - ĐHQGHN",
        "Core Focus: Data Structures & Algorithms, Advanced Database Systems, Network Security, Software Architecture, AI-Driven Development": "Trọng tâm đào tạo: Cấu trúc dữ liệu và giải thuật, Hệ quản trị cơ sở dữ liệu nâng cao, An toàn thông tin mạng, Kiến trúc phần mềm, Phát triển phần mềm hướng AI",
        "TECHNICAL SKILLS": "KỸ NĂNG KỸ THUẬT",
        "Languages: Python, C#, C/C++, SQL, Go, JavaScript, TypeScript": "Ngôn ngữ lập trình: Python, C#, C/C++, SQL, Go, JavaScript, TypeScript",
        "LLM & Agent Engineering: Google Antigravity SDK, Agentic Workflows, Prompt Engineering, Structured Markdown Outputs, Token Optimization": "Công nghệ LLM & Agent: Google Antigravity SDK, Agentic Workflows, Prompt Engineering, Định dạng đầu ra Markdown cấu trúc, Tối ưu hóa Token tiêu thụ",
        "Deep Learning & AI: PyTorch, TensorFlow/Keras, scikit-learn, OpenCV, U-Net, Bi-LSTM, Model Fine-tuning, Feature Extraction": "Học sâu & AI: PyTorch, TensorFlow/Keras, scikit-learn, OpenCV, U-Net, Bi-LSTM, Fine-tuning mô hình, Trích xuất đặc trưng",
        "Web Development: React, FastAPI, Flask, Vite, REST API Design, Responsive UI/UX": "Phát triển Web: React, FastAPI, Flask, Vite, Thiết kế REST API, Thiết kế Responsive UI/UX",
        "Systems & Architecture: Stream Processing, Async/Parallel Programming, System Architecture, Repository Pattern": "Hệ thống & Kiến trúc: Xử lý luồng dữ liệu (Stream Processing), Lập trình bất đồng bộ/Song song, Kiến trúc hệ thống, Repository Pattern",
        "Cybersecurity & DevSecOps: Penetration Testing, OWASP Top 10, WAF Configuration, Burp Suite, SonarQube": "An ninh mạng & DevSecOps: Đánh giá bảo mật (Penetration Testing), OWASP Top 10, Cấu hình WAF, Burp Suite, SonarQube",
        "Frameworks & Tools: Git, Docker, Docker Compose, Linux Systems, Arduino IDE, Unity Engine": "Công cụ & Khung phát triển: Git, Docker, Docker Compose, Hệ điều hành Linux, Arduino IDE",
        "EXPERIENCE": "KINH NGHIỆM LÀM VIỆC",
        "Data & Algorithmic Optimization Specialist  |  Independent Tech & Growth Solutions  Mar 2024 – Present": "Chuyên viên Tối ưu hóa Dữ liệu và Thuật toán  |  Independent Tech & Growth Solutions  Th3 2024 – Hiện tại",
        "Analyzed multi-platform content distribution algorithms (TikTok, Shopee) to optimize content structures and improve organic search visibility.": "Phân tích và nghiên cứu sâu thuật toán phân phối nội dung trên các nền tảng lớn (TikTok, Shopee) nhằm tối ưu hóa cấu trúc dữ liệu và cải thiện khả năng hiển thị tự nhiên.",
        "Developed data processing pipelines to clean, structure, and format digital asset metadata, ensuring compliance with automated platform listing policies.": "Xây dựng và phát triển các đường ống xử lý dữ liệu (data pipelines) làm sạch, cấu trúc hóa và định dạng siêu dữ liệu (metadata) của tài sản số, đảm bảo tuân thủ tuyệt đối các chính sách kiểm duyệt của nền tảng.",
        "Leveraged metric analytics (CTR, Conversion Rates) to perform A/B testing on digital assets, increasing user engagement and retention.": "Sử dụng các công cụ phân tích chỉ số (CTR, Tỷ lệ chuyển đổi) để tiến hành thử nghiệm A/B trên các tài sản kỹ thuật số, gia tăng tỷ lệ tương tác và giữ chân người dùng.",
        "PROJECTS": "DỰ ÁN TIÊU BIỂU",
        "AI Security WAF & Active Vulnerability Scanner  |  Python · TensorFlow/Keras · Flask · Docker       Jan 2026 – May 2026": "Tường lửa WAF & Bộ quét lỗ hổng bảo mật ứng dụng AI  |  Python · TensorFlow/Keras · Flask · Docker  Th1 2026 – Th5 2026",
        "Developed an active vulnerability scanner and passive WAF powered by a Bi-LSTM deep learning model achieving 99.68% accuracy classifying 7 attack categories (SQLi, XSS, SSRF, CSRF, Path Traversal, Command Injection) across 58K+ training samples.": "Xây dựng công cụ quét lỗ hổng bảo mật chủ động và hệ thống Tường lửa ứng dụng Web (WAF) thụ động dựa trên mô hình Học sâu (kiến trúc Bi-LSTM) đạt độ chính xác phân loại tấn công lên đến 99.68% đối với các mối đe dọa.",
        "Implemented multi-vector vulnerability simulation payloads to automate scanning and generate vulnerability reports in JSON and Markdown formats.": "Thiết lập các payload mô phỏng lỗ hổng đa vector (SQLi, XSS, SSRF, Path Traversal) để tự động hóa quét lỗi bảo mật và tạo báo cáo ở dạng JSON và Markdown.",
        "Built an AI Hacker Brain module using Groq API (Llama) for dynamic payload generation and active auditing via AI chaining.": "Tích hợp module AI Hacker Brain sử dụng Groq API (Llama) để tự động tạo payload động và kiểm tra tính bảo mật của hệ thống.",
        "Deployed a Flask reverse-proxy WAF with rate limiting, auto IP blacklisting, and a glassmorphism web console for real-time threat monitoring.": "Triển khai reverse-proxy WAF dựa trên Flask với giới hạn tần suất yêu cầu (rate limiting), tự động chặn IP xấu và bảng điều khiển trực quan thời gian thực.",
        "Autonomous Job Application & Recruitment AI Agent  |  Python · Google Antigravity SDK · Gemini API  Mar 2026 – Jun 2026": "Hệ thống AI Agent tự động hóa tìm kiếm việc làm & tuyển dụng  |  Python · Google Antigravity SDK · Gemini API  Th3 2026 – Th6 2026",
        "Engineered an autonomous multi-tool AI Agent using Google Antigravity SDK to automate CV parsing, job search queries, and application logging.": "Ứng dụng Google Antigravity SDK để phát triển AI Agent tự quản lý đa công cụ có khả năng tự động hóa phân tích CV cá nhân, truy vấn tìm kiếm việc làm và ghi nhật ký ứng tuyển.",
        "Designed custom functional tools for parsing resumes, searching recruitment databases, and exporting ATS-friendly cover letters in structured Markdown.": "Thiết kế các Custom Tools tích hợp khả năng đọc tài liệu thô, gọi API cơ sở dữ liệu tuyển dụng và xuất thư xin việc Cover Letter định dạng Markdown đáp ứng hoàn hảo tiêu chí của hệ thống ATS.",
        "Medical Cell Segmentation & Counting System  |  Python · PyTorch · OpenCV · Flask   Mar 2026 – May 2026": "Hệ thống phân tách và đếm tế bào y tế  |  Python · PyTorch · OpenCV · Flask   Th3 2026 – Th5 2026",
        "Built an end-to-end deep learning pipeline using U-Net trained on MoNuSeg 2018 for automated cell nuclei segmentation and counting on histopathological tissue.": "Xây dựng đường ống học máy hoàn chỉnh sử dụng kiến trúc mạng U-Net huấn luyện trên bộ dữ liệu ảnh y tế MoNuSeg 2018 phục vụ phân tách và đếm nhân tế bào tự động.",
        "Engineered preprocessing modules for image patching with overlap handling and normalization; containerized the full inference stack with Docker.": "Thiết kế module tiền xử lý ảnh (patching) xử lý chồng lấp và chuẩn hóa; đóng gói triển khai toàn bộ mô hình bằng Docker.",
        "Developed a Flask web application with dynamic diagram rendering and automated PDF report generation for clinical research use.": "Phát triển dashboard dựa trên Flask hiển thị biểu đồ phân tích động trực quan hóa mẫu tế bào và tích hợp công cụ tự động xuất báo cáo định dạng PDF.",
        "Scalable Research Paper Search Engine  |  React · TypeScript · FastAPI · SQL   Jan 2026 – Mar 2026": "Hệ thống tìm kiếm đề tài nghiên cứu khoa học quy mô lớn  |  React · TypeScript · FastAPI · SQL   Th1 2026 – Th3 2026",
        "Architected a high-throughput metadata repository for VNU academic publications using decoupled Repository Pattern with React/TypeScript frontend and FastAPI backend.": "Thiết kế kiến trúc kho lưu trữ siêu dữ liệu hiệu năng cao cho các công bố khoa học của Đại học Quốc gia bằng mô hình Repository Pattern tách biệt giữa React/TypeScript (Frontend) và FastAPI (Backend).",
        "Implemented debounced search with type-safe interfaces and an AI-powered semantic search API layer; orchestrated full-stack deployment via Docker Compose.": "Xây dựng các custom React hooks tối ưu hóa tìm kiếm (debounced search) với kiểu dữ liệu type-safe, tích hợp lớp API tìm kiếm ngữ nghĩa bằng AI; đóng gói triển khai bằng Docker Compose.",
        "Cross-Platform Clipboard Translator  |  Python · Bash · System APIs Sep 2025 – Dec 2025": "Công cụ dịch thuật clipboard đa nền tảng chạy ngầm  |  Python · Bash · System APIs  Th9 2025 – Th12 2025",
        "Built a zero-dependency translation utility for Linux, macOS, and Windows via native system APIs; implemented a Linux daemon monitoring text selection events and delivering real-time desktop notifications.": "Phát triển công cụ dịch thuật không phụ thuộc thư viện ngoài hoạt động mượt mà trên Linux, macOS và Windows thông qua API gốc; dịch vụ daemon chạy ngầm tự động dịch văn bản được bôi đen và hiển thị thông báo."
    }

    for p in doc.paragraphs:
        original_text = p.text.strip()
        # Tìm key khớp chính xác hoặc khớp gần đúng để dịch
        for eng, vi in translations.items():
            if eng in original_text:
                # Nếu đây là dòng tiêu đề phụ, ta có thể thay thế run để giữ format, 
                # hoặc thay toàn bộ text nếu không có style đặc biệt.
                p.text = p.text.replace(eng, vi)
                break
                
    doc.save('/home/truongan/Downloads/resume_truongan_vi.docx')
    print("Dịch DOCX thành công!")

if __name__ == "__main__":
    main()
