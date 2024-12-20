from archytas.tool_utils import tool
from dataclasses import dataclass
from pathlib import Path
import os


# Consider using claude/anthropic for this!
"""
Behavioral issues:
- try not to duplicate too much. instead of duplication, you should have a primary source, and link to the primary content/sections from other pages
- most edits should be verbatim or very close to it unless the user specifies it should be reworded.
   - exceptions include if splitting something out into sections, you can slightly reword the beginning/end if it makes the sections flow into each other
- do not make big assumptions about what the user wants. Collect information first to understand the full picture, and then ask for clarification on possible ambiguities
   - generally you should dialog a bit with the user (while also collecting information at the same time) to build up a picture of what they actually want
   - spend time building up context before deciding on what exactly to modify. e.g. read the content of possibly relevant pages
   # perhaps the agent could have a scratch pad it fills up with info before it makes edits
"""



"""
Design ideas/notes:
    [editor agent] -> archytas agent
      - have a context that it can add sections to
      - alternatively:
          ---> keep track of all pages the agent views
          ---> any time a page is viewed, elide any previously viewed pages in the chat history
          ---> OR see if we can get in on openai caching of chat history since they get long
      - find relevant sections. selected sections go into the context
          ---> sections are identified by the filename/section name so the agent can make links
      - manage the context (e.g. mark sections as done)
          ---> when marking a section as done, the section disappears, and is replaced with a short summary of it? don't want to overflow context
      - insert tool (wiki[start:end] = <new content>)
      - create a new page
    
    [bulk management]
    - create a new wiki (done by the user)



Test ideas:
- use existing wikis
    - one piece
    - lotgh
    - wikipedia (ultimate stress test )
- dat/mann work
- dogfood with jataware/slack

"""
# TODO: later set up with git and remote, and add gh-action for building wiki
def new_wiki(name: str):
    """
    make a folder for the wiki
    cd into the directory
    add a .wikimage file that indicates this directory is a wikimage managed wiki
    add .gitignore (include .wikimage)
    """
    root = Path(name)
    root.mkdir()
    os.chdir(root)
    wiki_init()


def wiki_init():
    """
    initialize a wikimage-managed wiki in the current directory
    """
    root = Path(".")
    (root / ".wikimage").touch()
    (root / ".gitignore").write_text("# wikimage identifier\n.wikimage\n")



"""
markdown.extensions.fenced_code
markdown.extensions.tables
"""
    


@dataclass
class Edit:
    start: int
    end: int
    content: str

# @dataclass
# class Insert:
#     start: int
#     content: str

# @dataclass
# class Delete:
#     start: int
#     end: int


# AGENT_NOTES = 

class WikiManager:
    """
    A set of tools for managing a wiki.
    
    General notes to keep in mind:
    - all wiki content should be valid markdown
    - use [[Page Name]] to link to other pages
    - page names may not include slashes 
    - edits are specified with line numbers. start is inclusive, end is exclusive (like a python slice)
    - to insert without deleting, make an edit where start=end
    - to delete without inserting, make an edit where content=""
    - when making edits, you should always view the page first to see the current content
    """
    # TODO: actually want to support slashes in titles... but means filename doesn't match title... perhaps title should be set at the top of the page markdown via metadata..

    # @tool
    # """maybe have an inner agent that checks each based on e.g. RAG compare or just looking at each whole page. prompt to call this tool: 'please describe broadly what kind of information you wish to modify in the wiki'"""
    # def find_relevant_sections(content: str): ...

    @staticmethod
    def get_page_path_by_name(name: str) -> Path:
        # search the whole tree for {name}.md
        for page in Path(".").glob("**/*.md"):
            if page.stem == name:
                return page
        raise FileNotFoundError(f"Page '{name}' does not exist. Please create the page before editing it.")

    
    @staticmethod
    @tool
    # TODO: allow the agent to put files into specific folders
    def create_new_page(name: str, content: str):
        """
        Create a new wiki page with the given content

        Args:
            name (str): the name of the new page
            content (str): the content of the new page. Should be valid markdown
        """
        file = Path(name).with_suffix(".md")
        if file.exists():
            raise FileExistsError(f"Page '{name}' already exists. Please choose a different name, or use the edit tool.")
        file.write_text(content)
    
    @staticmethod
    @tool
    def delete_page(name: str):
        """
        Delete a wiki page

        Args:
            name (str): the name of the page to delete
        """
        file = WikiManager.get_page_path_by_name(name)
        file.unlink()

    
    # TODO: swap this in if Edits is not working very well with the agent
    # @tool
    # def edit_page(pagename: str, inserts: list[Insert], deletes: list[Delete]):
    #     """
    #     Edit a wiki page

    #     Args:
    #         pagename (str): the name of the page to edit
    #         inserts (list[Insert]): a list of insertions to make to the page
    #         deletes (list[Delete]): a list of deletions to make to the page
    #     """

    @staticmethod
    @tool
    def edit_page(name: str, edits: list[Edit]) -> str:
        """
        Edit a wiki page

        Args:
            name (str): the name of the page to edit
            edits (list[Edit]): a list of edits to make to the page.

        Returns:
            str: a copy of the page after the edits have been made
        """
        file = WikiManager.get_page_path_by_name(name)
        content = file.read_text()
        lines = content.split("\n")

        # verify that the edits are in bounds
        for edit in edits:
            if edit.start < 0 or edit.end > len(lines):
                raise ValueError(f"Edit ({edit.start}, {edit.end}) is out of bounds. Page only has {len(lines)} lines. Please ensure that the edit is within the bounds of the page")

        # verify that the edits don't overlap
        for i, edit1 in enumerate(edits):
            for j, edit2 in enumerate(edits):
                if i != j and edit1.start < edit2.end and edit1.end > edit2.start:
                    raise ValueError(f"Edits {i} ({edit1.start}, {edit1.end}) and {j} ({edit2.start}, {edit2.end}) overlap. Please ensure that edits do not overlap")
        
        # apply edits in reverse order so that the indices don't change
        for edit in sorted(edits, key=lambda x: x.start, reverse=True):
            lines[edit.start:edit.end] = [edit.content]
        
        file.write_text("\n".join(lines))

        return WikiManager.view_page(name)


    @staticmethod
    @tool
    def list_pages() -> list[str]:
        """
        Display a list of all pages in the wiki

        Returns:
            list[str]: a list of all pages in the wiki
        """
        return sorted([page.stem for page in Path(".").glob("**/*.md")])
 
    @staticmethod
    @tool
    def view_page(name: str) -> str:
        """
        View the content of a page (with line numbers)

        Args:
            name (str): the name of the page to view

        Returns:
            str: the content of the page
        """
        file = WikiManager.get_page_path_by_name(name)

        # return the text with line numbers prepended to each line
        lines = file.read_text().split("\n")
        num_digits = len(str(len(lines)))
        numbered_lines = [f"{str(i).rjust(num_digits)}: {line}" for i, line in enumerate(lines)]
        return "\n".join(numbered_lines)
    
    # @staticmethod
    # @tool
    # def get_outgoing_links(name: str) -> list[str]:
    #     """
    #     Get a list of all pages that the given page links to

    #     Args:
    #         name (str): the name of the page to get links from

    #     Returns:
    #         list[str]: a set of all pages that are linked to in the given page
    #     """
    #     file = Path(name).with_suffix(".md")
    #     if not file.exists():
    #         raise FileNotFoundError(f"Page '{name}' does not exist. Please create the page before getting links from it.")
        
    #     # find all links in the file. could use regex, but this is safer and simpler
    #     links = set()
    #     text = file.read_text()
    #     start = 0
    #     while True:
    #         # find the next link
    #         start = text.find("[[", start)
    #         if start == -1:
    #             break
    #         end = text.find("]]", start)
    #         if end == -1:
    #             break
    #         link = text[start + 2:end]
    #         start = end + 2

    #         # Filter out invalid links
    #         if '\n' in link:
    #             print(f"Warning: page '{name}' contains a link that spans multiple lines: {link}")
    #             continue
    #         if not Path(f"{link}.md").exists():
    #             print(f"Warning: page '{name}' contains a link to a non-existent page: {link}")
    #             continue
            
    #         # add the link to the set
    #         links.add(link)

    #     return links
    

    # @staticmethod
    # @tool
    # def get_incoming_links(name: str) -> list[str]:
    #     """
    #     Get a list of all pages that link to the given page

    #     Args:
    #         name (str): the name of the page to get incoming links to

    #     Returns:
    #         list[str]: a set of all pages that link to the given page
    #     """
    #     incoming_links = set()
    #     for page in Path(".").glob("*.md"):
    #         text = page.read_text()
    #         if f"[[{name}]]" in text:
    #             incoming_links.add(page.stem)
    #     return incoming_links



    # @tool
    # def observe_image(): ... #so agent can look at images that are otherwise not shown to agent to save tokens







