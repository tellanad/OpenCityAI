from crewai import Agent, Task, Crew

crawler = Agent(
    role ="City Dcoeumnt crwaler",
    goal="Find Updated City Documents"
)

parser =Agent(
    role="Document Parser",
    goal="Find updated city Documents"
)

embedder=Agent(
    role="Embedding Generator",
    goal="Generate Vector Embeddings"
)

task1 = Task(
    description="Find updated documents",
    agent=crawler
)

task2 = Task(
    description="Parse documents",
    agent=parser
)

task3 = Task(
    description="Generate embeddings",
    agent=embedder
)

crew= Crew(
    agents=[crawler,parser,embedder],
    tasks=[task1, task2, task3]
)

crew.kickoff()