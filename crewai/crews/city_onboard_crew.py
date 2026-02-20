from crewai import Crew,Task, Agent



def create_city_discovery_agent():

    return Agent(
        role="City Discovery Specialist",

        goal=(
            "Identify city metadata, official domains, and initialize "
            "city configuration for onboarding into OpenCity AI platform."
        ),

        backstory=(
            "You are responsible for onboarding new cities. You locate "
            "official city websites, validate domain authenticity, and "
            "prepare configuration metadata."
        ),

        verbose=True,
        allow_delegation=False
    )
    
def create_data_source_agent():

    return Agent(
        role="Municipal Data Source Specialist",

        goal=(
            "Identify official knowledge sources including regulations, "
            "service portals, and public documentation."
        ),

        backstory=(
            "You analyze city domains and extract URLs relevant to permits, "
            "services, policies, and procedures."
        ),

        verbose=True,
        allow_delegation=False
    )
    
def create_crawler_agent():

    return Agent(
        role="Municipal Web Crawler",

        goal=(
            "Fetch and extract content from municipal knowledge sources "
            "accurately and efficiently."
        ),

        backstory=(
            "You retrieve structured and unstructured content from official "
            "city websites and prepare it for ingestion."
        ),

        verbose=True,
        allow_delegation=False
    )

def create_ingestion_agent():

    return Agent(
        role="Knowledge Ingestion Specialist",

        goal=(
            "Transform crawled content into structured chunks and store "
            "them into the vector database."
        ),

        backstory=(
            "You prepare data for semantic retrieval by chunking text, "
            "generating embeddings, and indexing into the OpenCity AI vector database."
        ),

        verbose=True,
        allow_delegation=False
    )

def create_verification_agent():

    return Agent(
        role="Knowledge Verification Specialist",

        goal=(
            "Verify correctness, completeness, and retrieval readiness "
            "of ingested knowledge."
        ),

        backstory=(
            "You ensure that vector database entries are accurate, properly "
            "indexed, and usable by the OpenCity AI retrieval system."
        ),

        verbose=True,
        allow_delegation=False
    )

def create_city_discovery_task(agent, city_name):

    return Task(
        description=f"Discover official domain and metadata for city: {city_name}",

        expected_output=(
            "Official city domain, metadata, and configuration parameters."
        ),

        agent=agent
    )
def create_data_source_task(agent, city_domain):

    return Task(
        description=f"Identify official knowledge sources from domain: {city_domain}",

        expected_output=(
            "List of URLs for services, permits, policies, and regulations."
        ),

        agent=agent
    )

def create_crawl_task(agent, sources):

    return Task(
        description=f"Crawl and extract content from sources: {sources}",

        expected_output="Structured content ready for ingestion.",

        agent=agent
    )
def create_ingestion_task(agent):

    return Task(
        description="Chunk, embed, and index content into vector database.",

        expected_output="Content successfully indexed into vector DB.",

        agent=agent
    )
def create_verification_task(agent):

    return Task(
        description="Verify vector database ingestion quality and completeness.",

        expected_output="Verification report confirming ingestion success.",

        agent=agent
    )
#onboarding    
def run_onboarding(city_name):
    discovery_agent = create_city_discovery_agent()
    data_agent = create_data_source_agent()
    crawler_agent = create_crawler_agent()
    ingestion_agent = create_ingestion_agent()
    verification_agent = create_verification_agent()
    
    task1 = create_city_discovery_task(discovery_agent, city_name)
    task2 = create_data_source_task(data_agent, "city_domain_placeholder")
    task3 = create_crawl_task(crawler_agent, "sources_placeholder")
    task4 = create_ingestion_task(ingestion_agent)
    task5 = create_verification_task(verification_agent)

    crew = Crew(
        agents=[
            discovery_agent,
            data_agent,
            crawler_agent,
            ingestion_agent,
            verification_agent
        ],

        tasks=[task1, task2, task3, task4, task5],

        verbose=True
    )
    
    result = crew.kickoff()

    return result