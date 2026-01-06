"""Chat Management Core Logic"""
from ..common_imports import *
from ..models.chat_models import ChatMessage, ChatSettings
from ..models.api_config import APIConfig

class ChatTree:
    """Manages the tree structure of chat messages"""
    def __init__(self):
        self.messages: Dict[str, ChatMessage] = {}  # id -> message
        self.roots: List[str] = []  # Root message IDs (user messages)
    
    def add_message(self, message: ChatMessage) -> str:
        """Add a message to the tree - UPDATED to handle retry scenarios"""
        self.messages[message.id] = message
        
        if message.role == "user":
            # Try to attach to last active assistant message
            last_assistant_id = self._find_last_active_assistant()
            if last_assistant_id:
                message.parent_id = last_assistant_id
                parent = self.messages[last_assistant_id]
                message.sibling_index = len(parent.children_ids)
                parent.children_ids.append(message.id)
            else:
                # No assistant response yet — treat as root
                self.roots.append(message.id)
                message.parent_id = None

        else:  # assistant message
            # Find the most recent active user message as parent
            if self.roots:
                parent_id = self._find_active_parent()
                if parent_id:
                    message.parent_id = parent_id
                    parent = self.messages[parent_id]
                    
                    # Set sibling index
                    message.sibling_index = len(parent.children_ids)
                    parent.children_ids.append(message.id)
        
        return message.id
   



    def _find_active_child(self, message_id: str) -> Optional[str]:
        """Find the active child of a message"""
        message = self.messages.get(message_id)
        if not message:
            return None
        
        for child_id in message.children_ids:
            child = self.messages.get(child_id)
            if child and child.is_active:
                return child_id
        
        return None

    def _promote_to_root(self, message_id: str):
        """
        Promote a message to be a root node, preserving its entire subtree.
        This is the key improvement - it preserves the conversation tree below.
        """
        message = self.messages.get(message_id)
        if not message:
            return
        
        # Remove from old parent's children list
        if message.parent_id and message.parent_id in self.messages:
            old_parent = self.messages[message.parent_id]
            if message_id in old_parent.children_ids:
                old_parent.children_ids.remove(message_id)
                # Update sibling indices for remaining children
                for i, child_id in enumerate(old_parent.children_ids):
                    if child_id in self.messages:
                        self.messages[child_id].sibling_index = i
        
        # Make it a root
        message.parent_id = None
        message.sibling_index = len(self.roots)
        
        # Add to roots if not already there
        if message_id not in self.roots:
            self.roots.append(message_id)
        
        print(f"📌 Message promoted to root: {message.content[:30]}...")

    def _remove_message_preserving_children(self, message_id: str):
        """
        Remove a single message after its active children have been promoted.
        Only removes the message itself, not its descendants.
        """
        if message_id not in self.messages:
            return
        
        message = self.messages[message_id]
        
        # Remove from parent's children or from roots
        if message.parent_id and message.parent_id in self.messages:
            parent = self.messages[message.parent_id]
            if message_id in parent.children_ids:
                parent.children_ids.remove(message_id)
                # Update sibling indices
                for i, child_id in enumerate(parent.children_ids):
                    if child_id in self.messages:
                        self.messages[child_id].sibling_index = i
        else:
            # Remove from roots
            if message_id in self.roots:
                self.roots.remove(message_id)
        
        # Handle inactive children - they get deleted with parent
        for child_id in list(message.children_ids):
            child = self.messages.get(child_id)
            if child and not child.is_active:
                # Recursively delete inactive branches
                self._delete_branch_recursive(child_id)
        
        # Delete the message itself
        del self.messages[message_id]
        print(f"🗑️ Removed message: {message.content[:30]}...")






   
    def _find_last_active_assistant(self) -> Optional[str]:
        """Find the most recent active assistant message - UPDATED"""
        # Get the active conversation path and find the last assistant message
        active_path = self.get_active_conversation_path()
        
        # Traverse backwards to find the last active assistant message
        for msg in reversed(active_path):
            if msg.role == "assistant" and msg.is_active:
                return msg.id
        
        return None
        
    def _find_active_parent(self) -> Optional[str]:
        """Find the most recent active user message - UPDATED"""
        # Get the active conversation path and find the last user message
        active_path = self.get_active_conversation_path()
        
        # Traverse backwards to find the last active user message
        for msg in reversed(active_path):
            if msg.role == "user" and msg.is_active:
                return msg.id
        
        return None
    
    def edit_message(self, message_id: str, new_content: str) -> str:
        """Edit a message, creating a new branch"""
        original = self.messages.get(message_id)
        if not original:
            return message_id
        
        # Create new message at same level
        new_message = ChatMessage(
            role=original.role,
            content=new_content,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            parent_id=original.parent_id,
            sibling_index=original.sibling_index + 1
        )
        
        # Deactivate original and its descendants
        self._deactivate_branch(message_id)
        
        # Add new message
        self.messages[new_message.id] = new_message
        
        # Update parent's children if exists
        if original.parent_id:
            parent = self.messages[original.parent_id]
            # Insert new message after original
            insert_index = parent.children_ids.index(message_id) + 1
            parent.children_ids.insert(insert_index, new_message.id)
            
            # Update sibling indices
            for i, child_id in enumerate(parent.children_ids):
                self.messages[child_id].sibling_index = i
        else:
            # It's a root message
            insert_index = self.roots.index(message_id) + 1
            self.roots.insert(insert_index, new_message.id)
        
        return new_message.id
    def _activate_descendants(self, parent_id: str):
        """Activate the first active descendant path from a parent"""
        parent = self.messages.get(parent_id)
        if not parent or not parent.children_ids:
            return
        
        # Find the first active child, or activate the first child if none are active
        active_child = None
        for child_id in parent.children_ids:
            child = self.messages.get(child_id)
            if child and child.is_active:
                active_child = child_id
                break
        
        if not active_child and parent.children_ids:
            # No active children, activate the first one
            active_child = parent.children_ids[0]
            self.messages[active_child].is_active = True
        
        if active_child:
            self._activate_descendants(active_child)
        
    def delete_message(self, message_id: str):
        """Delete a specific message and only its descendants - FIXED to preserve siblings"""
        if message_id not in self.messages:
            print(f"Warning: Message {message_id} not found in tree")
            return
        
        message = self.messages[message_id]
        
        print(f"Deleting message: {message.content[:50]}... (ID: {message_id})")
        print(f"Message has {len(message.children_ids)} children")
        
        # CRITICAL: Before deletion, find and activate a sibling if this was the active one
        was_active = message.is_active
        parent_id = message.parent_id
        
        # Step 1: Remove from parent's children list OR from roots
        if message.parent_id and message.parent_id in self.messages:
            parent = self.messages[message.parent_id]
            if message_id in parent.children_ids:
                parent.children_ids.remove(message_id)
                print(f"Removed from parent {message.parent_id}")
                
                # CRITICAL: If this was the active message and there are siblings, activate the first one
                if was_active and parent.children_ids:
                    # Find siblings with same role
                    siblings = [child_id for child_id in parent.children_ids 
                            if child_id in self.messages and 
                            self.messages[child_id].role == message.role]
                    
                    if siblings:
                        # Activate the first sibling
                        first_sibling_id = siblings[0]
                        first_sibling = self.messages[first_sibling_id]
                        first_sibling.is_active = True
                        print(f"Activated sibling: {first_sibling.content[:30]}... (ID: {first_sibling_id})")
                        
                        # Activate its descendants too
                        self._activate_descendants(first_sibling_id)
                
                # Update sibling indices for remaining children
                for i, child_id in enumerate(parent.children_ids):
                    if child_id in self.messages:
                        self.messages[child_id].sibling_index = i
        else:
            # It's a root message
            if message_id in self.roots:
                self.roots.remove(message_id)
                print(f"Removed from roots")
                
                # CRITICAL: If this was an active root and there are other roots, activate one
                if was_active and self.roots:
                    first_root = self.messages[self.roots[0]]
                    first_root.is_active = True
                    self._activate_descendants(self.roots[0])
        
        # Step 2: Recursively delete this message and all its descendants
        self._delete_branch_recursive(message_id)
        
        print(f"Delete operation completed. Remaining messages: {len(self.messages)}")



    def _delete_branch_recursive(self, message_id: str):
        """Recursively delete a message and all its descendants - FIXED VERSION"""
        if message_id not in self.messages:
            return
        
        message = self.messages[message_id]
        
        print(f"Recursively deleting: {message.content[:30]}... (ID: {message_id})")
        
        # First, recursively delete all children
        children_to_delete = list(message.children_ids)  # Create a copy to avoid modification during iteration
        for child_id in children_to_delete:
            self._delete_branch_recursive(child_id)
        
        # Then delete this message
        del self.messages[message_id]
        print(f"Deleted message: {message_id}")


    def _deactivate_branch(self, message_id: str, recursive: bool = True):
        if message_id in self.messages:
            self.messages[message_id].is_active = False
            if recursive:
                for child_id in self.messages[message_id].children_ids:
                    self._deactivate_branch(child_id, recursive)
    
    def _delete_branch(self, message_id: str):
        """Delete a message and all its descendants"""
        if message_id in self.messages:
            message = self.messages[message_id]
            # Delete all children first
            for child_id in list(message.children_ids):
                self._delete_branch(child_id)
            # Delete this message
            del self.messages[message_id]
    
    def get_siblings(self, message_id: str) -> List[str]:
        """Get all sibling message IDs"""
        message = self.messages.get(message_id)
        if not message:
            return []
        
        if message.parent_id:
            parent = self.messages[message.parent_id]
            return [child_id for child_id in parent.children_ids 
                    if self.messages[child_id].role == message.role]
        else:
            # Root message - get other roots
            return self.roots
    
    def get_active_conversation_path(self) -> List[ChatMessage]:
        """Get the currently active conversation path - UPDATED"""
        result = []
        
        # Start from roots and follow active branches
        for root_id in self.roots:
            root = self.messages[root_id]
            if root.is_active:
                result.append(root)
                self._collect_active_children(root_id, result)
        
        return result
        
    def _collect_active_children(self, parent_id: str, result: List[ChatMessage]):
        """Recursively collect active children - UPDATED"""
        parent = self.messages[parent_id]
        for child_id in parent.children_ids:
            child = self.messages[child_id]
            if child.is_active:
                result.append(child)
                self._collect_active_children(child_id, result)



class PromptFormatter:
    """Handle different prompt formats for various models"""
    
    @staticmethod
    def format_system_message(config: APIConfig, character_name: str, personality: str, user_context: str = "") -> str:
        """Format system message based on model preferences"""
        
        # Use the custom template from config
        base_template = config.system_message_template.format(
            character_name=character_name,
            personality=personality
        )
        
        if config.use_role_context and user_context:
            base_template += f"\n\nUser Context: {user_context}"
        
        if config.use_chain_of_thought:
            base_template += "\n\nThink step by step before responding."
        
        if config.output_format_instruction:
            base_template += f"\n\nOutput Format: {config.output_format_instruction}"

        
        return base_template
    
    @staticmethod
    def format_conversation(config: APIConfig, messages: List[dict]) -> List[dict]:
        """Format conversation history based on instruction format"""
        
        if config.instruction_format == "alpaca":
            return PromptFormatter._format_alpaca(messages, config)
        elif config.instruction_format == "chatml":
            return PromptFormatter._format_chatml(messages, config)
        elif config.instruction_format == "vicuna":
            return PromptFormatter._format_vicuna(messages, config)
        elif config.instruction_format == "llama":
            return PromptFormatter._format_llama(messages, config)
        else:
            return PromptFormatter._format_default(messages, config)
    
    @staticmethod
    def _format_alpaca(messages: List[dict], config: APIConfig) -> List[dict]:
        """Format for Alpaca-style models"""
        formatted = []
        for msg in messages:
            if msg["role"] == "user":
                content = f"### Instruction:\n{msg['content']}\n\n### Response:"
            else:
                content = msg["content"]
            formatted.append({"role": msg["role"], "content": content})
        return formatted
    
    @staticmethod
    def _format_chatml(messages: List[dict], config: APIConfig) -> List[dict]:
        """Format for ChatML-style models"""
        formatted = []
        for msg in messages:
            if msg["role"] == "user":
                content = f"<|im_start|>user\n{msg['content']}<|im_end|>"
            else:
                content = f"<|im_start|>assistant\n{msg['content']}<|im_end|>"
            formatted.append({"role": msg["role"], "content": content})
        return formatted
    
    @staticmethod
    def _format_vicuna(messages: List[dict], config: APIConfig) -> List[dict]:
        """Format for Vicuna-style models"""
        formatted = []
        for msg in messages:
            if msg["role"] == "user":
                content = f"USER: {msg['content']}\nASSISTANT:"
            else:
                content = msg["content"]
            formatted.append({"role": msg["role"], "content": content})
        return formatted
    
    @staticmethod
    def _format_llama(messages: List[dict], config: APIConfig) -> List[dict]:
        """Format for Llama-style models"""
        formatted = []
        for msg in messages:
            if msg["role"] == "user":
                content = f"[INST] {msg['content']} [/INST]"
            else:
                content = msg["content"]
            formatted.append({"role": msg["role"], "content": content})
        return formatted
    
    @staticmethod
    def _format_default(messages: List[dict], config: APIConfig) -> List[dict]:
        """Default formatting with custom prefixes"""
        return messages

