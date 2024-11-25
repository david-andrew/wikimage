from .tool import WikiManager
from archytas.react import ReActAgent, FailedTaskError
from easyrepl import REPL

def main():
    tools=[WikiManager]
    agent = ReActAgent(model='gpt-4o', tools=tools, verbose=True)
    print(agent.prompt)

    # REPL to interact with agent
    for query in REPL(history_file='../.chat'):
        try:
            answer = agent.react(query)
            print(answer)
        except FailedTaskError as e:
            print(f"Error: {e}")



if __name__ == '__main__':
    main()