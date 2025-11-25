#!/usr/bin/python
"""
LLM Chess Player - Integrates Large Language Models for chess move generation
Demonstrates complex AI algorithm design, optimization, and decision-making systems
"""

import os
import json
import re
from typing import Optional, Tuple, List
from game.board import Board

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class LLMPlayer:
    """
    Chess player that uses LLMs to generate moves.
    Converts board state to FEN notation, queries LLM, and parses responses.
    """
    
    def __init__(self, provider: str = "openai", model: str = "gpt-4", api_key: Optional[str] = None):
        """
        Initialize LLM player
        
        Args:
            provider: "openai" or "anthropic"
            model: Model name (e.g., "gpt-4", "claude-3-opus-20240229")
            api_key: API key (if None, reads from environment or config)
        """
        self.provider = provider.lower()
        self.model = model
        self.api_key = api_key or self._load_api_key()
        self.move_history = []  # Store move history for context
        self.promotion_piece = None  # Store promotion piece if needed
        
        # Initialize API client
        if self.provider == "openai":
            if not OPENAI_AVAILABLE:
                raise ImportError("openai package not installed. Install with: pip install openai")
            if not self.api_key:
                raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable or provide api_key parameter.")
            self.client = openai.OpenAI(api_key=self.api_key)
        elif self.provider == "anthropic":
            if not ANTHROPIC_AVAILABLE:
                raise ImportError("anthropic package not installed. Install with: pip install anthropic")
            if not self.api_key:
                raise ValueError("Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable or provide api_key parameter.")
            self.client = Anthropic(api_key=self.api_key)
        else:
            raise ValueError(f"Unsupported provider: {provider}. Use 'openai' or 'anthropic'")
    
    def _load_api_key(self) -> Optional[str]:
        """Load API key from environment or config file"""
        # Try environment variables first
        if self.provider == "openai":
            key = os.getenv("OPENAI_API_KEY")
        else:
            key = os.getenv("ANTHROPIC_API_KEY")
        
        # Try config file
        if not key:
            config_path = os.path.join(os.path.dirname(__file__), "..", "..", "llm_config.json")
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        config = json.load(f)
                        key = config.get(f"{self.provider}_api_key")
                except:
                    pass
        
        return key
    
    def board_to_fen(self, board: Board) -> str:
        """
        Convert board state to FEN (Forsyth-Edwards Notation)
        
        Args:
            board: Board object
            
        Returns:
            FEN string representation of the board
        """
        fen_parts = []
        board_state = board.getBoard()
        
        # Convert board to FEN piece placement
        # FEN reads from rank 8 (top/Black) to rank 1 (bottom/White)
        # In this board: y=0 is rank 8 (Black), y=7 is rank 1 (White)
        for row in range(8):  # row 0 = rank 8, row 7 = rank 1
            fen_row = ""
            empty_count = 0
            
            for col in range(8):  # col 0 = a-file, col 7 = h-file
                piece = board_state[col][row]  # board[x][y] where x=col, y=row
                piece_type = piece.returnType()
                piece_color = piece.returnColor()
                
                if piece_type == "blank":
                    empty_count += 1
                else:
                    if empty_count > 0:
                        fen_row += str(empty_count)
                        empty_count = 0
                    
                    # Map piece types to FEN notation
                    piece_map = {
                        "King": "K", "Queen": "Q", "Rook": "R",
                        "Bishop": "B", "Knight": "N", "Pawn": "P"
                    }
                    fen_char = piece_map.get(piece_type, "")
                    if piece_color == "Black":
                        fen_char = fen_char.lower()
                    fen_row += fen_char
            
            if empty_count > 0:
                fen_row += str(empty_count)
            
            fen_parts.append(fen_row)
        
        # Combine rows with '/'
        fen_position = "/".join(fen_parts)
        
        # Add active color (w = white, b = black)
        active_color = "w" if board.checkTurn() == 0 else "b"
        
        # Castling rights (simplified - would need to track rook/king moves)
        castling = "KQkq"  # Assume all castling available (can be improved)
        
        # En passant target square (simplified)
        en_passant = "-"
        
        # Halfmove clock (simplified)
        halfmove = "0"
        
        # Fullmove number
        fullmove = str(len(self.move_history) // 2 + 1)
        
        # Combine all parts
        fen = f"{fen_position} {active_color} {castling} {en_passant} {halfmove} {fullmove}"
        
        return fen
    
    def algebraic_to_coords(self, move: str, board: Board) -> Optional[Tuple[int, int, int, int]]:
        """
        Convert algebraic notation (e.g., "e4", "Nf3", "Qxe5") to board coordinates
        
        Args:
            move: Algebraic notation string
            board: Current board state
            
        Returns:
            Tuple of (prevR, prevC, newR, newC) or None if invalid
        """
        move = move.strip().upper()
        
        # Remove check/checkmate symbols
        move = move.replace("+", "").replace("#", "")
        
        # Handle castling
        if move == "O-O" or move == "0-0":  # Kingside castling
            return self._handle_castling(board, True)
        if move == "O-O-O" or move == "0-0-0":  # Queenside castling
            return self._handle_castling(board, False)
        
        # Parse piece type, source, destination, capture
        piece_type = None
        source_file = None
        source_rank = None
        dest_file = None
        dest_rank = None
        is_capture = "x" in move or "X" in move
        
        # Handle pawn promotion (e.g., "e8=Q", "d1=N")
        promotion_piece = None
        if "=" in move:
            parts = move.split("=")
            if len(parts) == 2:
                move = parts[0]  # Move without promotion
                promotion_char = parts[1].strip().upper()
                promotion_map = {"Q": "Queen", "R": "Rook", "B": "Bishop", "N": "Knight"}
                promotion_piece = promotion_map.get(promotion_char)
        
        # Extract destination square (always last 2 chars if not castling)
        if len(move) >= 2:
            dest = move[-2:]
            if dest[0] in "ABCDEFGH" and dest[1] in "12345678":
                dest_file = ord(dest[0]) - ord("A")
                dest_rank = 8 - int(dest[1])  # Convert to 0-7 (rank 8 = row 0)
        
        # Remove destination from move string
        move_without_dest = move[:-2] if len(move) >= 2 else move
        move_without_dest = move_without_dest.replace("x", "").replace("X", "")
        
        # Determine piece type
        if move_without_dest.startswith("K"):
            piece_type = "King"
            move_without_dest = move_without_dest[1:]
        elif move_without_dest.startswith("Q"):
            piece_type = "Queen"
            move_without_dest = move_without_dest[1:]
        elif move_without_dest.startswith("R"):
            piece_type = "Rook"
            move_without_dest = move_without_dest[1:]
        elif move_without_dest.startswith("B"):
            piece_type = "Bishop"
            move_without_dest = move_without_dest[1:]
        elif move_without_dest.startswith("N"):
            piece_type = "Knight"
            move_without_dest = move_without_dest[1:]
        else:
            # Default to pawn if no piece specified
            piece_type = "Pawn"
        
        # Extract source disambiguation (file or rank)
        if len(move_without_dest) > 0:
            if move_without_dest[0] in "ABCDEFGH":
                source_file = ord(move_without_dest[0]) - ord("A")
            elif move_without_dest[0] in "12345678":
                source_rank = 8 - int(move_without_dest[0])
        
        # Find matching piece
        board_state = board.getBoard()
        current_turn = board.checkTurn()
        target_color = "White" if current_turn == 0 else "Black"
        
        candidates = []
        for col in range(8):
            for row in range(8):
                piece = board_state[col][row]
                if (piece.returnType() == piece_type and 
                    piece.returnColor() == target_color):
                    
                    # Check if this piece can move to destination
                    if board.isLegal(col, row, dest_file, dest_rank, True):
                        # Apply source disambiguation filters
                        if source_file is not None and col != source_file:
                            continue
                        if source_rank is not None and row != source_rank:
                            continue
                        candidates.append((col, row, dest_file, dest_rank))
        
        # Return first valid candidate (or None if ambiguous/invalid)
        if len(candidates) == 1:
            result = candidates[0]
            # Store promotion piece if specified (will be handled by game logic)
            if promotion_piece:
                self.promotion_piece = promotion_piece
            return result
        elif len(candidates) > 1:
            # If multiple candidates, try to disambiguate further
            # For now, return first one (could be improved)
            result = candidates[0]
            if promotion_piece:
                self.promotion_piece = promotion_piece
            return result
        
        return None
    
    def _handle_castling(self, board: Board, kingside: bool) -> Optional[Tuple[int, int, int, int]]:
        """Handle castling moves"""
        current_turn = board.checkTurn()
        if current_turn == 0:  # White
            king_col, king_row = 4, 7
            if kingside:
                rook_col, rook_row = 7, 7
                new_king_col = 6
            else:
                rook_col, rook_row = 0, 7
                new_king_col = 2
        else:  # Black
            king_col, king_row = 4, 0
            if kingside:
                rook_col, rook_row = 7, 0
                new_king_col = 6
            else:
                rook_col, rook_row = 0, 0
                new_king_col = 2
        
        # Check if castling is legal
        if board.isLegal(king_col, king_row, new_king_col, king_row, True):
            return (king_col, king_row, new_king_col, king_row)
        
        return None
    
    def get_llm_move(self, board: Board, max_retries: int = 3) -> Optional[Tuple[int, int, int, int]]:
        """
        Query LLM for a chess move
        
        Args:
            board: Current board state
            max_retries: Maximum number of retry attempts
            
        Returns:
            Tuple of (prevR, prevC, newR, newC) or None if failed
        """
        fen = self.board_to_fen(board)
        
        # Build prompt
        prompt = self._build_chess_prompt(fen)
        
        for attempt in range(max_retries):
            try:
                # Query LLM
                response_text = self._query_llm(prompt)
                
                # Extract move from response
                move = self._extract_move_from_response(response_text)
                
                if move:
                    # Convert to coordinates
                    coords = self.algebraic_to_coords(move, board)
                    
                    if coords:
                        # Validate move is legal
                        prevR, prevC, newR, newC = coords
                        if board.isLegal(prevR, prevC, newR, newC, True):
                            self.move_history.append(move)
                            return coords
                
                # If we get here, move extraction/validation failed
                if attempt < max_retries - 1:
                    print(f"LLM returned invalid move: {response_text}. Retrying...")
                    continue
                    
            except Exception as e:
                print(f"Error querying LLM (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    continue
        
        return None
    
    def _build_chess_prompt(self, fen: str) -> str:
        """Build prompt for LLM"""
        prompt = f"""You are a chess grandmaster. Analyze the following chess position and provide your best move in standard algebraic notation (e.g., e4, Nf3, Qxe5, O-O).

Current position (FEN): {fen}

Provide ONLY the move in algebraic notation, nothing else. Examples of valid moves:
- Pawn moves: e4, d5, exd5
- Knight moves: Nf3, Nxe5
- Bishop moves: Bc4, Bxf7
- Rook moves: Ra1, Rxe8
- Queen moves: Qd4, Qxf7
- King moves: Ke2, Kxe1
- Castling: O-O (kingside), O-O-O (queenside)
- Pawn promotion: e8=Q, d1=N (use =Q, =R, =B, or =N for promotion)

Move:"""
        return prompt
    
    def _query_llm(self, prompt: str) -> str:
        """Query the LLM API"""
        if self.provider == "openai":
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a chess grandmaster. Respond with only the move in algebraic notation."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Lower temperature for more deterministic moves
                max_tokens=10
            )
            return response.choices[0].message.content.strip()
        
        elif self.provider == "anthropic":
            response = self.client.messages.create(
                model=self.model,
                max_tokens=10,
                temperature=0.3,
                system="You are a chess grandmaster. Respond with only the move in algebraic notation.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.content[0].text.strip()
    
    def _extract_move_from_response(self, response: str) -> Optional[str]:
        """Extract move from LLM response"""
        # Clean response
        response = response.strip()
        
        # Remove common prefixes/suffixes
        response = re.sub(r"^(Move|The move|Best move|I would play|I'll play)[:\s]*", "", response, flags=re.IGNORECASE)
        response = re.sub(r"[\.\s]*$", "", response)
        
        # Extract first valid-looking move pattern
        # Match algebraic notation patterns
        move_patterns = [
            r"O-O-O",  # Queenside castling
            r"O-O",    # Kingside castling
            r"[KQRNB]?[a-h]?[1-8]?x?[a-h][1-8]",  # Standard moves
            r"[a-h][1-8]",  # Simple pawn moves
        ]
        
        for pattern in move_patterns:
            match = re.search(pattern, response, re.IGNORECASE)
            if match:
                return match.group(0).upper()
        
        # If no pattern matched, try to extract first word/token
        tokens = response.split()
        if tokens:
            return tokens[0].upper()
        
        return None
    
    def playMove(self, board: Board) -> bool:
        """
        Play a move using LLM
        
        Args:
            board: Current board state
            
        Returns:
            True if move was played successfully, False otherwise
        """
        move_coords = self.get_llm_move(board)
        
        if move_coords:
            self.xChoiceI, self.yChoiceI, self.xChoiceN, self.yChoiceN = move_coords
            return True
        
        return False
    
    def getxChoiceI(self) -> int:
        """Get initial X coordinate (column)"""
        return self.xChoiceI
    
    def getyChoiceI(self) -> int:
        """Get initial Y coordinate (row)"""
        return self.yChoiceI
    
    def getxChoiceN(self) -> int:
        """Get new X coordinate (column)"""
        return self.xChoiceN
    
    def getyChoiceN(self) -> int:
        """Get new Y coordinate (row)"""
        return self.yChoiceN

