#!/bin/bash

# ==============================================================================
# FB Job Tracker - Auto Deploy Script
# ==============================================================================

# Harmonious colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0;68m' # No Color
BOLD='\033[1m'

echo -e "${BLUE}${BOLD}======================================================================${NC}"
echo -e "${BLUE}${BOLD}          🚀 SYSTEM AUTO-DEPLOYMENT UTILITY - FB JOB TRACKER          ${NC}"
echo -e "${BLUE}${BOLD}======================================================================${NC}"

WORKING_DIR=$(pwd)
CURRENT_USER=$(whoami)

# Pre-flight check: Load environmental variables
if [ -f .env ]; then
    export $(cat .env | xargs)
fi

show_menu() {
    echo -e "\n${BOLD}Chọn hình thức triển khai (Choose deployment option):${NC}"
    echo -e "  ${GREEN}1)${NC} Triển khai làm dịch vụ chạy ngầm cục bộ (${BOLD}Local systemd service${NC})"
    echo -e "  ${GREEN}2)${NC} Triển khai bằng container hóa (${BOLD}Docker Compose${NC})"
    echo -e "  ${GREEN}3)${NC} Thiết lập lịch tự động cào tin mỗi ngày (${BOLD}Cron Job Daily Scraper${NC})"
    echo -e "  ${GREEN}4)${NC} Chạy thử nghiệm ngay trong background (${BOLD}FastAPI dev server background${NC})"
    echo -e "  ${RED}5) Thoát (Exit)${NC}"
    echo -ne "\nLựa chọn của bạn [1-5]: "
}

deploy_systemd() {
    echo -e "\n${BLUE}[1/4] Đang khởi tạo systemd service file...${NC}"
    
    # Read GEMINI_API_KEY
    if [ -z "$GEMINI_API_KEY" ]; then
        echo -ne "${YELLOW}Nhập GEMINI_API_KEY của bạn (hoặc Enter để bỏ qua): ${NC}"
        read -r INPUT_KEY
        GEMINI_API_KEY=$INPUT_KEY
    fi

    # Generate custom service file
    SERVICE_FILE="fb_job_tracker.service"
    cp config/fb_job_tracker.service.template "$SERVICE_FILE"
    
    # Replace placeholders
    sed -i "s|{USER}|$CURRENT_USER|g" "$SERVICE_FILE"
    sed -i "s|{WORKING_DIR}|$WORKING_DIR|g" "$SERVICE_FILE"
    sed -i "s|{GEMINI_API_KEY}|$GEMINI_API_KEY|g" "$SERVICE_FILE"

    echo -e "${GREEN}✔ Đã sinh file cấu hình systemd: $SERVICE_FILE${NC}"
    echo -e "\n${YELLOW}Yêu cầu quyền sudo để cài đặt service vào hệ thống...${NC}"
    
    sudo cp "$SERVICE_FILE" /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable fb_job_tracker
    sudo systemctl restart fb_job_tracker

    echo -e "\n${GREEN}🎉 Đã triển khai systemd service thành công!${NC}"
    echo -e "Trạng thái hiện tại:"
    sudo systemctl status fb_job_tracker --no-pager
    echo -e "\n${BLUE}👉 Web Dashboard đang chạy tại: http://localhost:8000${NC}"
}

deploy_docker() {
    echo -e "\n${BLUE}Đang bắt đầu triển khai bằng Docker Compose...${NC}"
    
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Lỗi: Chưa cài đặt Docker trên hệ thống! Vui lòng cài đặt Docker và thử lại.${NC}"
        return 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        echo -e "${RED}❌ Lỗi: Chưa cài đặt Docker Compose!${NC}"
        return 1
    fi

    # Check for .env file
    if [ ! -f .env ]; then
        echo -e "${YELLOW}Tạo tệp .env mặc định...${NC}"
        echo "GEMINI_API_KEY=$GEMINI_API_KEY" > .env
    fi

    echo -e "${BLUE}Đang build image và khởi chạy các service...${NC}"
    if command -v docker-compose &> /dev/null; then
        docker-compose up -d --build
    else
        docker compose up -d --build
    fi

    echo -e "\n${GREEN}🎉 Đã khởi chạy thành công container Docker ở chế độ chạy ngầm (detached mode)!${NC}"
    echo -e "${BLUE}👉 Web Dashboard đang chạy tại: http://localhost:8000${NC}"
    echo -e "Sử dụng lệnh '${BOLD}docker logs -f fb_job_tracker${NC}' để xem logs thời gian thực."
}

setup_cron() {
    echo -e "\n${BLUE}Đang thiết lập lịch cào tin tự động hàng ngày (Daily Auto Scraper)...${NC}"
    
    CRON_CMD="0 8 * * * cd $WORKING_DIR && $WORKING_DIR/.venv/bin/python src/fb_job_bot.py --headless >> $WORKING_DIR/cron_scraper.log 2>&1"
    
    # Check if already in crontab
    (crontab -l 2>/dev/null | grep -F "fb_job_bot.py") &>/dev/null
    if [ $? -eq 0 ]; then
        echo -e "${YELLOW}Lịch cào tin đã tồn tại trong crontab. Đang cập nhật...${NC}"
        # Remove old entry and add new
        (crontab -l 2>/dev/null | grep -v -F "fb_job_bot.py"; echo "$CRON_CMD") | crontab -
    else
        # Add new entry
        (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
    fi

    echo -e "${GREEN}✔ Đã thêm cron job thành công! Bot sẽ tự động chạy vào lúc 08:00 mỗi ngày.${NC}"
    echo -e "Kiểm tra danh sách cron hiện tại bằng lệnh: ${BOLD}crontab -l${NC}"
}

run_dev_background() {
    echo -e "\n${BLUE}Khởi chạy server FastAPI chạy ngầm bằng nohup...${NC}"
    
    # Check if port 8000 is occupied
    if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
        echo -e "${RED}❌ Lỗi: Cổng 8000 đang được sử dụng bởi một tiến trình khác!${NC}"
        return 1
    fi

    nohup "$WORKING_DIR/.venv/bin/python" -m uvicorn src.app:app --host 0.0.0.0 --port 8000 > app.log 2>&1 &
    
    echo -e "${GREEN}✔ Đã khởi chạy FastAPI server chạy ngầm (PID: $!).${NC}"
    echo -e "Logs được lưu tại: ${BOLD}app.log${NC}"
    echo -e "${BLUE}👉 Truy cập Web Dashboard tại: http://localhost:8000${NC}"
}

# Run menu loop
while true; do
    show_menu
    read -r choice
    case $choice in
        1)
            deploy_systemd
            break
            ;;
        2)
            deploy_docker
            break
            ;;
        3)
            setup_cron
            break
            ;;
        4)
            run_dev_background
            break
            ;;
        5)
            echo -e "\nTạm biệt!"
            exit 0
            ;;
        *)
            echo -e "${RED}Lựa chọn không hợp lệ! Vui lòng chọn lại.${NC}"
            ;;
    esac
done
