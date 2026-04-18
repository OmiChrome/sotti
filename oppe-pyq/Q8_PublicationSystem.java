import java.util.*;

/**
 * QUESTION: Copy Constructor - Author/PublicationSystem (Sep 2024 OPPE1 - Session 1, Type 1)
 * ============================================================================
 * Problem Statement:
 * In a publication system, Author a1 contributes to a set of books. Author a2
 * also contributes to all the books contributed by a1 except the second book,
 * which a2 replaces with another book. Define two classes Author and
 * PublicationSystem. Define a copy constructor to create a2 from a1 such that
 * changing the values of instance variables of either a2 or a1 does not affect
 * the other one. The program accepts name of author a2 and the new book
 * contributed by a2 as input.
 *
 * Class Author has/should have:
 *   - Private instance variables: String name and String[] books
 *   - Define required constructor(s) (parameterized + copy constructor)
 *   - Accessor methods: getName() and getBook(int)
 *   - Mutator methods: setName(String) and setBook(int, String)
 *
 * Class PublicationSystem main():
 *   - Creates a1 ("Nandu", books) and a2 (copy of a1)
 *   - Updates a2's name and second book from input
 *   - Prints name+second book of a1, then name+second book of a2
 *
 * What you have to do:
 *   - Define a constructor to initialize instance variables in Author
 *   - Define a copy constructor for deep copy of another Author object
 *
 * Test Cases:
 *   Input: Suba COA  →  Output: Nandu: DL \n Suba: COA
 *   Input: Pai CV    →  Output: Nandu: DL \n Pai: CV
 *   Input: Neha DS   →  Output: Nandu: DL \n Neha: DS
 *   Input: Srinu MLP →  Output: Nandu: DL \n Srinu: MLP
 */

class Author {
    private String name;
    private String[] books;

    //***** Define constructor(s) here
    Author(String n,String[] b){name=n;books=b.clone();}
    Author(Author a){this(a.name,a.books);}

    public void setName(String n) {
        name = n;
    }
    public void setBook(int indx, String b) {
        books[indx] = b;
    }
    public String getName() {
        return name;
    }
    public String getBook(int indx) {
        return books[indx];
    }
}

public class Q8_PublicationSystem {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        String[] books = {"Maths", "DL", "DSA", "DC"};
        Author a1 = new Author("Nandu", books);
        Author a2 = new Author(a1);
        a2.setName(sc.next());
        a2.setBook(1, sc.next());
        System.out.println(a1.getName() + ": " + a1.getBook(1));
        System.out.println(a2.getName() + ": " + a2.getBook(1));
    }
}
