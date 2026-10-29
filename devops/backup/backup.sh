#!/bin/bash
# WIN OS Database Backup Script
# Production-ready backup automation

set -o errexit
set -o nounset
set -o pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

# Environment variables (can be overridden via Docker or .env)
POSTGRES_HOST=${POSTGRES_HOST:-postgres}
POSTGRES_PORT=${POSTGRES_PORT:-5432}
POSTGRES_USER=${POSTGRES_USER:-timescale}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-password}
POSTGRES_DB=${POSTGRES_DB:-wasteintel}
BACKUP_DIR=${BACKUP_DIR:-/backups}
BACKUP_SCHEDULE=${BACKUP_SCHEDULE:-0 2 * * *}
BACKUP_RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}
BACKUP_TYPE=${BACKUP_TYPE:-full}
LOG_LEVEL=${LOG_LEVEL:-INFO}

# ============================================================================
# LOGGING FUNCTIONS
# ============================================================================

log_debug() {
    if [[ "${LOG_LEVEL}" == "DEBUG" ]]; then
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] [DEBUG] $1"
    fi
}

log_info() {
    if [[ "${LOG_LEVEL}" == "DEBUG" || "${LOG_LEVEL}" == "INFO" ]]; then
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] [INFO] $1"
    fi
}

log_warn() {
    if [[ "${LOG_LEVEL}" == "DEBUG" || "${LOG_LEVEL}" == "INFO" || "${LOG_LEVEL}" == "WARN" ]]; then
        echo "[$(date +'%Y-%m-%d %H:%M:%S')] [WARN] $1" >&2
    fi
}

log_error() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [ERROR] $1" >&2
}

# ============================================================================
# BACKUP FUNCTIONS
# ============================================================================

# Create directory if it doesn't exist
ensure_backup_dir() {
    if [[ ! -d "${BACKUP_DIR}" ]]; then
        log_info "Creating backup directory: ${BACKUP_DIR}"
        mkdir -p "${BACKUP_DIR}"
    fi
}

# Generate backup filename
generate_backup_filename() {
    local timestamp=$(date +'%Y%m%d_%H%M%S')
    local backup_name="wasteintel_${timestamp}"
    
    case "${BACKUP_TYPE}" in
        full)
            echo "${backup_name}_full.dump"
            ;;
        logical)
            echo "${backup_name}_logical.sql"
            ;;
        custom)
            echo "${backup_name}_custom.dump"
            ;;
        *)
            echo "${backup_name}_full.dump"
            ;;
    esac
}

# Perform database backup
perform_backup() {
    local backup_file="${BACKUP_DIR}/$(generate_backup_filename)"
    local start_time=$(date +%s)
    
    log_info "Starting ${BACKUP_TYPE} backup of ${POSTGRES_DB}..."
    log_debug "Backup file: ${backup_file}"
    
    case "${BACKUP_TYPE}" in
        full)
            # Full database backup using pg_dump
            log_info "Performing full database backup..."
            PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
                -h "${POSTGRES_HOST}" \
                -p "${POSTGRES_PORT}" \
                -U "${POSTGRES_USER}" \
                -d "${POSTGRES_DB}" \
                -F c \
                -f "${backup_file}" \
                -v --no-password 2>&1 | while read -r line; do log_debug "pg_dump: $line"; done
            ;;
        logical)
            # Logical backup (SQL format)
            log_info "Performing logical database backup..."
            PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
                -h "${POSTGRES_HOST}" \
                -p "${POSTGRES_PORT}" \
                -U "${POSTGRES_USER}" \
                -d "${POSTGRES_DB}" \
                -f "${backup_file}" \
                -v --no-password 2>&1 | while read -r line; do log_debug "pg_dump: $line"; done
            ;;
        custom)
            # Custom backup with specific options
            log_info "Performing custom database backup..."
            PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
                -h "${POSTGRES_HOST}" \
                -p "${POSTGRES_PORT}" \
                -U "${POSTGRES_USER}" \
                -d "${POSTGRES_DB}" \
                -F c \
                -f "${backup_file}" \
                --no-owner \
                --no-privileges \
                -v --no-password 2>&1 | while read -r line; do log_debug "pg_dump: $line"; done
            ;;
        *)
            # Default to full backup
            log_info "Performing default full database backup..."
            PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
                -h "${POSTGRES_HOST}" \
                -p "${POSTGRES_PORT}" \
                -U "${POSTGRES_USER}" \
                -d "${POSTGRES_DB}" \
                -F c \
                -f "${backup_file}" \
                -v --no-password 2>&1 | while read -r line; do log_debug "pg_dump: $line"; done
            ;;
    esac
    
    local end_time=$(date +%s)
    local duration=$((end_time - start_time))
    local file_size=$(stat -c%s "${backup_file}" 2>/dev/null || echo "0")
    
    log_info "Backup completed in ${duration} seconds"
    log_info "Backup file size: ${file_size} bytes"
    log_info "Backup saved to: ${backup_file}"
    
    # Create metadata file
    local metadata_file="${BACKUP_DIR}/$(basename "${backup_file}" .dump).metadata.json"
    cat > "${metadata_file}" <<EOF
{
  "backup_name": "$(basename "${backup_file}")",
  "database": "${POSTGRES_DB}",
  "host": "${POSTGRES_HOST}",
  "type": "${BACKUP_TYPE}",
  "start_time": "$(date -d @"${start_time}" +'%Y-%m-%dT%H:%M:%SZ')",
  "end_time": "$(date -d @"${end_time}" +'%Y-%m-%dT%H:%M:%SZ')",
  "duration_seconds": ${duration},
  "file_size_bytes": ${file_size},
  "retention_days": ${BACKUP_RETENTION_DAYS}
}
EOF
    
    log_debug "Backup metadata saved to: ${metadata_file}"
    
    return 0
}

# Verify backup integrity
verify_backup() {
    local backup_file="${1}"
    
    if [[ ! -f "${backup_file}" ]]; then
        log_error "Backup file not found: ${backup_file}"
        return 1
    fi
    
    log_info "Verifying backup: ${backup_file}"
    
    # Check if file is readable
    if [[ ! -r "${backup_file}" ]]; then
        log_error "Backup file is not readable: ${backup_file}"
        return 1
    fi
    
    # Check file size
    local file_size=$(stat -c%s "${backup_file}")
    if [[ ${file_size} -eq 0 ]]; then
        log_error "Backup file is empty: ${backup_file}"
        return 1
    fi
    
    log_info "Backup verification successful: ${backup_file}"
    return 0
}

# Clean up old backups
cleanup_old_backups() {
    log_info "Cleaning up backups older than ${BACKUP_RETENTION_DAYS} days..."
    
    local cutoff_date=$(date -d "${BACKUP_RETENTION_DAYS} days ago" +'%Y%m%d_%H%M%S')
    local backup_count=0
    local deleted_count=0
    
    for backup_file in "${BACKUP_DIR}"/wasteintel_*.dump; do
        if [[ -f "${backup_file}" ]]; then
            backup_count=$((backup_count + 1))
            
            # Extract timestamp from filename
            local filename=$(basename "${backup_file}")
            local file_date=${filename#wasteintel_}
            file_date=${file_date%_*}
            
            # Compare dates
            if [[ "${file_date}" < "${cutoff_date}" ]]; then
                log_info "Deleting old backup: ${backup_file}"
                rm -f "${backup_file}"
                
                # Also delete metadata file
                local metadata_file="${BACKUP_DIR}/${filename%.dump}.metadata.json"
                if [[ -f "${metadata_file}" ]]; then
                    rm -f "${metadata_file}"
                fi
                
                deleted_count=$((deleted_count + 1))
            fi
        fi
    done
    
    log_info "Backup cleanup complete: ${deleted_count} backups deleted, ${backup_count} backups retained"
    return 0
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

main() {
    log_info "========================================"
    log_info "WIN OS Database Backup Script"
    log_info "========================================"
    log_info "Configuration:"
    log_info "  - Host: ${POSTGRES_HOST}"
    log_info "  - Database: ${POSTGRES_DB}"
    log_info "  - Backup Type: ${BACKUP_TYPE}"
    log_info "  - Retention: ${BACKUP_RETENTION_DAYS} days"
    log_info "  - Directory: ${BACKUP_DIR}"
    log_info "  - Log Level: ${LOG_LEVEL}"
    log_info "========================================"
    
    # Ensure backup directory exists
    ensure_backup_dir
    
    # Perform backup
    if ! perform_backup; then
        log_error "Backup failed!"
        exit 1
    fi
    
    # Get the backup file we just created
    local latest_backup=$(ls -t "${BACKUP_DIR}"/wasteintel_*.dump 2>/dev/null | head -n 1)
    
    # Verify backup
    if ! verify_backup "${latest_backup}"; then
        log_error "Backup verification failed!"
        exit 1
    fi
    
    # Clean up old backups
    if ! cleanup_old_backups; then
        log_warn "Backup cleanup encountered issues"
    fi
    
    log_info "Backup process completed successfully!"
    
    # If running as a cron job, exit cleanly
    if [[ "${RUN_AS_CRON:-false}" == "true" ]]; then
        exit 0
    fi
    
    # If running as a scheduled job in Docker, keep the container running
    # This allows for manual backup triggering via exec
    log_info "Backup container running. Use 'docker exec <container> /backup.sh' for manual backup."
    
    # Keep container running
    tail -f /dev/null
}

# ============================================================================
# CRON SETUP
# ============================================================================

# If BACKUP_SCHEDULE is set, configure cron
setup_cron() {
    if [[ -n "${BACKUP_SCHEDULE}" && "${BACKUP_SCHEDULE}" != "none" ]]; then
        log_info "Setting up cron schedule: ${BACKUP_SCHEDULE}"
        
        # Create cron entry
        echo "${BACKUP_SCHEDULE} /backup.sh" | crontab -
        
        # Start cron
        log_info "Starting cron service..."
        crond -f -l 2 &
        
        # Keep container running
        tail -f /dev/null
    fi
}

# ============================================================================
# ENTRYPOINT
# ============================================================================

# If this script is run as the main command in a container
if [[ "${0}" == "/backup.sh" || "${BASH_SOURCE[0]}" == "/backup.sh" ]]; then
    # Check if we should run as a scheduled job
    if [[ -n "${BACKUP_SCHEDULE}" && "${BACKUP_SCHEDULE}" != "none" ]]; then
        setup_cron
    else
        main
    fi
else
    # If sourced or run directly, just execute main
    main
fi
