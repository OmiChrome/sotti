## BLOCK
class Address implements Cloneable {
    private String addr;
    public Address(String addr) { this.addr = addr; }
    public String getAddr() { return addr; }
    public void setAddr(String addr) { this.addr = addr; }
    public Object clone() throws CloneNotSupportedException { return super.clone(); }
    public String toString() { return addr; }
}

class Department implements Cloneable {
    private String dept;
    public Department(String dept) { this.dept = dept; }
    public String getDept() { return dept; }
    public void setDept(String dept) { this.dept = dept; }
    public Object clone() throws CloneNotSupportedException { return super.clone(); }
    public String toString() { return dept; }
}

class Person implements Cloneable {
    private String name;
    private Address addr;
    public Person(String name, Address addr) { this.name = name; this.addr = addr; }
    public String getName() { return name; }
    public Address getAddr() { return addr; }
    public Person clone() throws CloneNotSupportedException {
        Person p = (Person) super.clone();
        p.addr = (Address) this.addr.clone();
        return p;
    }
}

class Employee extends Person implements Cloneable {
    private Department dept;
    public Employee(String name, Address addr, Department dept) { super(name, addr); this.dept = dept; }
    public Department getDept() { return dept; }
    public void updateEmp(String newAddr, String newDept) {
        getAddr().setAddr(newAddr);
        this.dept.setDept(newDept);
    }
    public Employee clone() throws CloneNotSupportedException {
        Employee e = (Employee) super.clone();
        e.dept = (Department) this.dept.clone();
        return e;
    }
    public String toString() { return getName() + " : " + getAddr() + " : " + dept; }
}

## FULL SOLUTION
```java
import java.util.*;

class Address implements Cloneable {
    private String addr;
    public Address(String addr) { this.addr = addr; }
    public String getAddr() { return addr; }
    public void setAddr(String addr) { this.addr = addr; }
    public Object clone() throws CloneNotSupportedException { return super.clone(); }
    public String toString() { return addr; }
}

class Department implements Cloneable {
    private String dept;
    public Department(String dept) { this.dept = dept; }
    public String getDept() { return dept; }
    public void setDept(String dept) { this.dept = dept; }
    public Object clone() throws CloneNotSupportedException { return super.clone(); }
    public String toString() { return dept; }
}

class Person implements Cloneable {
    private String name;
    private Address addr;
    public Person(String name, Address addr) { this.name = name; this.addr = addr; }
    public String getName() { return name; }
    public Address getAddr() { return addr; }
    public Person clone() throws CloneNotSupportedException {
        Person p = (Person) super.clone();
        p.addr = (Address) this.addr.clone();
        return p;
    }
}

class Employee extends Person implements Cloneable {
    private Department dept;
    public Employee(String name, Address addr, Department dept) { super(name, addr); this.dept = dept; }
    public Department getDept() { return dept; }
    public void updateEmp(String newAddr, String newDept) {
        getAddr().setAddr(newAddr);
        this.dept.setDept(newDept);
    }
    public Employee clone() throws CloneNotSupportedException {
        Employee e = (Employee) super.clone();
        e.dept = (Department) this.dept.clone();
        return e;
    }
    public String toString() { return getName() + " : " + getAddr() + " : " + dept; }
}

public class Solution {
    public static void main(String[] args){
        Scanner sc = new Scanner(System.in);
        if (!sc.hasNext()) return;
        String n = sc.next();
        String a1 = sc.next();
        String d1 = sc.next();
        String a2 = sc.next();
        String d2 = sc.next();
        try {
            Employee e1 = new Employee(n, new Address(a1), new Department(d1));
            Employee e2 = e1.clone();
            e1.updateEmp(a2, d2);
            System.out.println(e1 + ", " + e2);
        }
        catch(CloneNotSupportedException e) {
            System.out.println("clone() not supported");
        }
    }
}
```