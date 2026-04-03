"""Database operations for storing LiveKit session reports."""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
from config import DATABASE_PATH, DATABASE_DIR


class MedicalReportDB:
    """Database handler for LiveKit session reports."""
    
    def __init__(self, db_path: str = DATABASE_PATH):
        """Initialize database connection and create tables if needed."""
        self.db_path = db_path
        DATABASE_DIR.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Create tables if they don't exist."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS session_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                room_id TEXT,
                job_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                report_json TEXT NOT NULL,
                conversation_summary TEXT,
                duration REAL
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_id ON session_reports(session_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_job_id ON session_reports(job_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_created_at ON session_reports(created_at)
        """)
        
        conn.commit()
        conn.close()
    
    def save_session_report(
        self,
        session_id: str,
        report_data: Dict,
        job_id: str,
        room_id: Optional[str] = None,
    ):
        """Save a LiveKit session report to the database.
        
        Args:
            session_id: Unique session identifier
            report_data: Complete session report dictionary from LiveKit
            job_id: LiveKit job ID
            room_id: LiveKit room ID
            
        Returns:
            The ID of the saved report
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Extract conversation summary from chat history
        conversation_summary = None
        if "chat_history" in report_data and "messages" in report_data["chat_history"]:
            messages = report_data["chat_history"]["messages"]
            if messages:
                # Get the last few messages as summary
                summary_messages = messages[-10:] if len(messages) > 10 else messages
                conversation_summary = "\n".join([
                    f"{msg.get('role', 'unknown')}: {msg.get('content', '')}"
                    for msg in summary_messages
                    if isinstance(msg.get('content'), str)
                ])
        
        # Extract duration if available
        duration = report_data.get("duration")
        
        report_json = json.dumps(report_data, indent=2, ensure_ascii=False)
        
        cursor.execute("""
            INSERT INTO session_reports (
                session_id, room_id, job_id, report_json, 
                conversation_summary, duration
            ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            room_id,
            job_id,
            report_json,
            conversation_summary,
            duration
        ))
        
        report_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return report_id
    
    def get_report(self, report_id: int) -> Optional[Dict]:
        """Retrieve a report by ID."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM session_reports WHERE id = ?", (report_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def get_reports_by_session(self, session_id: str) -> List[Dict]:
        """Retrieve all reports for a session."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM session_reports WHERE session_id = ? ORDER BY created_at DESC",
            (session_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
