// ============================================
// RATTLE - Production JavaScript
// ============================================

console.log('✅ RATTLE loaded');

// ============================================
// Token Management Functions
// ============================================

function viewToken(id) {
    if (!id) return;
    
    fetch(`/api/token/${id}`)
        .then(r => r.json())
        .then(data => {
            const formatted = JSON.stringify(data, null, 2);
            showTokenModal(formatted);
        })
        .catch(() => alert('Failed to load token'));
}

function refreshToken(id) {
    if (!id) return;
    if (!confirm('Refresh this token?')) return;
    
    fetch(`/token/${id}/refresh`, { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                alert('✅ Token refreshed successfully!');
                location.reload();
            } else {
                alert('❌ Refresh failed: ' + data.error);
            }
        });
}

function showTokenModal(data) {
    const modal = document.createElement('div');
    modal.style.cssText = `
        position: fixed; top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(0,0,0,0.6); z-index: 10000;
        display: flex; align-items: center; justify-content: center;
        backdrop-filter: blur(4px);
    `;
    
    modal.innerHTML = `
        <div style="background: white; border-radius: 12px; max-width: 700px; max-height: 80vh; width: 90%; padding: 24px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); display: flex; flex-direction: column;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                <h3 style="margin: 0; color: #202124;"><i class="fas fa-key" style="color: #1a73e8;"></i> Token Details</h3>
                <button onclick="this.closest('div[style]').remove()" style="background: none; border: none; font-size: 24px; cursor: pointer; color: #5f6368;">×</button>
            </div>
            <pre style="background: #1e1e1e; color: #d4d4d4; padding: 16px; border-radius: 8px; overflow: auto; flex: 1; font-family: 'Courier New', monospace; font-size: 12px; line-height: 1.6; margin: 0;">${escapeHtml(data)}</pre>
            <div style="display: flex; gap: 10px; margin-top: 16px; justify-content: flex-end;">
                <button onclick="copyToClipboard('${escapeHtml(data)}')" style="background: #1a73e8; color: white; border: none; padding: 8px 20px; border-radius: 6px; cursor: pointer; font-size: 14px;">
                    <i class="fas fa-copy"></i> Copy
                </button>
                <button onclick="this.closest('div[style]').remove()" style="background: #f1f3f4; color: #202124; border: none; padding: 8px 20px; border-radius: 6px; cursor: pointer; font-size: 14px;">Close</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
}

function copyToClipboard(text) {
    if (!text) return;
    navigator.clipboard.writeText(text).then(() => {
        alert('Copied to clipboard!');
    }).catch(() => {
        // Fallback
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.left = '-9999px';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        alert('Copied to clipboard!');
    });
}

function escapeHtml(str) {
    return str.replace(/[&<>"]/g, function(m) {
        if (m === '&') return '&amp;';
        if (m === '<') return '&lt;';
        if (m === '>') return '&gt;';
        if (m === '"') return '&quot;';
        return m;
    });
}

// ============================================
// Campaign Management Functions
// ============================================

function deleteCampaign(id) {
    if (!id) return;
    if (!confirm('⚠️ Delete this campaign and all associated data? This cannot be undone.')) return;
    
    fetch(`/campaign/${id}/delete`, { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                alert('✅ Campaign deleted successfully!');
                location.reload();
            } else {
                alert('❌ Delete failed: ' + (data.error || 'Unknown error'));
            }
        });
}

function generateQR(campaignId) {
    if (!campaignId) return;
    
    fetch(`/campaign/${campaignId}/generate-qr`)
        .then(r => r.json())
        .then(data => {
            if (data.qr_code) {
                const container = document.getElementById('qrContainer');
                const img = document.getElementById('qrImage');
                if (container && img) {
                    img.src = 'data:image/png;base64,' + data.qr_code;
                    container.style.display = 'block';
                }
            }
        });
}

function copyUrl() {
    const urlInput = document.getElementById('phishingUrl');
    if (urlInput) {
        copyToClipboard(urlInput.value);
    }
}

// ============================================
// Auto-cleanup on page load
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ RATTLE ready for production');
});
