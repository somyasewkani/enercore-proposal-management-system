"""
Enercore AI Solar Proposal Generator
components/chatbot.py

Floating AI chatbot component:
- Chat bubble toggle button (bottom right)
- Expandable chat window with glassmorphism
- Quick action buttons
- Integration-ready message input

Designed to provide AI assistance on all pages.
"""

import streamlit as st


def _inject_chatbot_styles() -> None:
    """CSS for the floating chatbot with glassmorphism effects."""
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap');

            .enercore-chat-toggle {
                position: fixed;
                bottom: 2rem;
                right: 2rem;
                z-index: 999;
                width: 56px;
                height: 56px;
                border-radius: 50%;
                background: #006b1b;
                color: #ffffff;
                border: none;
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                box-shadow: 0 8px 24px rgba(0, 107, 27, 0.25);
                transition: all 0.2s ease;
            }

            .enercore-chat-toggle:hover {
                transform: scale(1.05);
                box-shadow: 0 12px 32px rgba(0, 107, 27, 0.35);
            }

            .enercore-chat-toggle-icon {
                font-family: 'Material Symbols Outlined';
                font-size: 28px;
            }

            .enercore-chat-window {
                position: fixed;
                bottom: 6rem;
                right: 2rem;
                z-index: 998;
                width: 320px;
                max-height: 480px;
                background: rgba(255, 255, 255, 0.85);
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                border: 1px solid rgba(255, 255, 255, 0.4);
                border-radius: 24px;
                display: flex;
                flex-direction: column;
                box-shadow: 0 16px 48px rgba(11, 61, 46, 0.15);
                overflow: hidden;
            }

            .enercore-chat-header {
                background: #006b1b;
                color: #ffffff;
                padding: 1rem 1.25rem;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }

            .enercore-chat-header-title {
                font-weight: 700;
                font-size: 0.95rem;
                display: flex;
                align-items: center;
                gap: 0.5rem;
            }

            .enercore-chat-body {
                flex: 1;
                padding: 1rem;
                overflow-y: auto;
                max-height: 280px;
            }

            .enercore-chat-message {
                display: flex;
                gap: 0.5rem;
                margin-bottom: 0.75rem;
            }

            .enercore-chat-avatar {
                width: 28px;
                height: 28px;
                border-radius: 50%;
                background: rgba(0, 107, 27, 0.2);
                display: flex;
                align-items: center;
                justify-content: center;
                flex-shrink: 0;
            }

            .enercore-chat-bubble {
                background: #f2f4f6;
                border-radius: 12px;
                padding: 0.6rem 0.85rem;
                font-size: 0.85rem;
                color: #191c1e;
                max-width: 85%;
            }

            .enercore-chat-input {
                padding: 0.75rem;
                border-top: 1px solid rgba(191, 202, 185, 0.2);
                background: #ffffff;
                display: flex;
                gap: 0.5rem;
            }

            .enercore-chat-input-field {
                flex: 1;
                border: 1px solid rgba(191, 202, 185, 0.3);
                border-radius: 12px;
                padding: 0.5rem 0.75rem;
                font-size: 0.85rem;
                outline: none;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_chatbot() -> None:
    """Render the floating AI chatbot component."""
    _inject_chatbot_styles()

    # Initialize chatbot state
    if "chat_open" not in st.session_state:
        st.session_state.chat_open = False

    # Chat toggle button
    col1, col2, col3 = st.columns([5, 1, 1])

    with col3:
        if st.button(
            "💬",
            key="chat_toggle",
            help="Enercore AI Assistant",
        ):
            st.session_state.chat_open = not st.session_state.chat_open

    # Chat window
    if st.session_state.chat_open:
        st.markdown(
            """
            <div class="enercore-chat-window">
                <div class="enercore-chat-header">
                    <div class="enercore-chat-header-title">
                        <span style="font-family: 'Material Symbols Outlined';">smart_toy</span>
                        Enercore Assistant
                    </div>
                    <button onclick="document.getElementById('chat_toggle').click()" style="background:none;border:none;color:white;cursor:pointer;font-family:'Material Symbols Outlined';font-size:20px;">close</button>
                </div>
                <div class="enercore-chat-body">
                    <div class="enercore-chat-message">
                        <div class="enercore-chat-avatar">
                            <span style="font-family: 'Material Symbols Outlined';font-size:16px;color:#006b1b;">smart_toy</span>
                        </div>
                        <div class="enercore-chat-bubble">
                            Hello! I'm your Enercore AI assistant. How can I help with your solar proposals today?
                        </div>
                    </div>
                </div>
                <div class="enercore-chat-input">
                    <input class="enercore-chat-input-field" placeholder="Type a message..." />
                    <button style="background:#006b1b;color:white;border:none;border-radius:10px;padding:0.5rem;width:36px;height:36px;cursor:pointer;">
                        <span style="font-family: 'Material Symbols Outlined';">send</span>
                    </button>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )