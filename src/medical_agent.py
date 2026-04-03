"""Medical symptom collection agent using LiveKit."""
from pathlib import Path
from datetime import datetime
from livekit.agents import Agent


class MedicalSymptomAgent(Agent):
    """Agent that collects symptoms from patients via voice calls.
    
    This agent:
    - Collects symptoms systematically through conversation
    - Does NOT provide diagnosis
    - Saves conversation transcript to text file
    """
    
    def __init__(self, session_id: str):
        """Initialize the medical symptom collection agent."""
        self.session_id = session_id
        self.conversation_history = []
        
        # Create reports directory
        self.reports_dir = Path(__file__).parent / "data" / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
        # System instructions for symptom collection
        instructions = """
        You are a professional medical intake assistant. Your role is to collect 
        symptom information from patients during phone calls. You are NOT a doctor 
        and you MUST NOT provide any diagnosis, medical advice, or treatment recommendations.
        
        Your responsibilities:
        1. Greet the patient warmly and professionally
        2. Collect patient information (name, age, gender) if not provided
        3. Systematically collect symptom information:
           - Primary symptoms (main complaints)
           - Secondary symptoms (related symptoms)
           - Symptom details (description, location, nature)
           - Duration (how long symptoms have been present)
           - Severity (mild, moderate, severe)
           - Onset (sudden or gradual)
           - Frequency (constant, intermittent, occasional)
           - Triggers (what makes symptoms worse)
           - Associated symptoms (other symptoms that occur together)
        4. Be empathetic, clear, and professional
        5. Ask one question at a time
        6. Confirm information when appropriate
        7. When you have collected sufficient information, summarize what you've collected
        
        CRITICAL RULES:
        - NEVER provide diagnosis, medical advice, or treatment recommendations
        - NEVER suggest medications or treatments
        - If asked about diagnosis or treatment, politely redirect: "I'm here to collect 
          your symptoms. A healthcare provider will review this information and provide 
          appropriate guidance."
        - Keep questions clear and simple
        - Be patient and understanding
        - All text you return will be spoken aloud, so avoid bullets, slashes, or 
          non-pronounceable punctuation
        - Speak naturally and conversationally
        """
        
        super().__init__(instructions=instructions)
    
    async def on_user_speech_committed(self, message):
        """Called when user speech is committed. Store the message."""
        print(f"👤 User: {message}")
        self.conversation_history.append({"role": "user", "content": message})
    
    async def on_agent_speech_committed(self, message):
        """Called when agent speech is committed. Store the message."""
        print(f"🤖 Agent: {message}")
        self.conversation_history.append({"role": "agent", "content": message})
    
    def save_transcript(self):
        """Save the conversation transcript to a text file."""
        print(f"\n{'='*80}")
        print("SAVING CONVERSATION TRANSCRIPT")
        print(f"{'='*80}\n")
        
        # Create full conversation transcript
        transcript_lines = []
        transcript_lines.append("="*80)
        transcript_lines.append("MEDICAL CONSULTATION TRANSCRIPT")
        transcript_lines.append("="*80)
        transcript_lines.append(f"Session ID: {self.session_id}")
        transcript_lines.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        transcript_lines.append("="*80)
        transcript_lines.append("")
        
        for msg in self.conversation_history:
            role = "PATIENT" if msg["role"] == "user" else "AGENT"
            transcript_lines.append(f"{role}: {msg['content']}")
            transcript_lines.append("")
        
        transcript_lines.append("="*80)
        transcript_lines.append("END OF TRANSCRIPT")
        transcript_lines.append("="*80)
        
        full_transcript = "\n".join(transcript_lines)
        
        # Print to console
        print(full_transcript)
        
        # Save to file
        filename = f"conversation_{self.session_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = self.reports_dir / filename
        
        # try:
        #     with open(filepath, 'w', encoding='utf-8') as f:
        #         f.write(full_transcript)
        #     print(f"\n✅ Transcript saved to: {filepath}")
        # except Exception as e:
        #     print(f"\n❌ Error saving transcript: {e}")
